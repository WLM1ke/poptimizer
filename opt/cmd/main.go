package main

import (
	"context"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/app"
	"github.com/WLM1ke/poptimizer/opt/internal/front"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/caarlos0/env/v6"
	"go.uber.org/goleak"
	"golang.org/x/sync/errgroup"
)

type config struct {
	App struct {
		GoroutineInterval time.Duration `envDefault:"1m"`
	}
	Server struct {
		Addr    string        `envDefault:"localhost:10000"`
		Timeout time.Duration `envDefault:"1s"`
	}
	HTTPClient struct {
		Connections int `envDefault:"20"`
	}
	MongoDB struct {
		URI string `env:"URI,unset" envDefault:"mongodb://localhost:27017"`
	}
	Telegram struct {
		Token  string `env:"TOKEN,unset"`
		ChatID string `env:"CHAT_ID,unset"`
	}
}

func main() {
	logger := lgr.New("App")

	defer atExit(logger)

	cfg := loadCfg(logger)
	appCtx := createCtx(logger, cfg.App.GoroutineInterval)

	run(appCtx, cfg, logger)
}

func atExit(logger *lgr.Logger) {
	if err := goleak.Find(); err != nil {
		logger.Warnf("stopped with exit code 1 -> found leaked goroutines")
		os.Exit(1)
	}

	if r := recover(); r != nil {
		logger.Warnf("stopped with exit code 1 -> %s", r)
		os.Exit(1)
	}

	logger.Infof("stopped with exit code 0")
	os.Exit(0)
}

func loadCfg(logger *lgr.Logger) (cfg config) {
	if err := env.Parse(&cfg); err != nil {
		logger.Panicf("can't load config -> %s", err)
	}

	logger.Infof("config loaded")

	return cfg
}

func createCtx(logger *lgr.Logger, interval time.Duration) context.Context {
	ctx, appCancel := context.WithCancel(context.Background())

	go func() {
		defer appCancel()

		ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
		defer cancel()

		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				logger.Infof("%d goroutines are running", runtime.NumGoroutine())
			case <-ctx.Done():
				logger.Infof("shutdown signal received")

				return
			}
		}
	}()

	return ctx
}

func run(appCtx context.Context, cfg config, logger *lgr.Logger) {
	httpClient := clients.NewHTTPClient(cfg.HTTPClient.Connections)
	defer httpClient.CloseIdleConnections()

	telegramClient, err := clients.NewTelegram(httpClient, cfg.Telegram.Token, cfg.Telegram.ChatID)
	if err != nil {
		logger.Panicf("can't create telegram client -> %s", err)
	}

	mongoClient, err := clients.NewMongoClient(cfg.MongoDB.URI)
	defer func() {
		err := mongoClient.Disconnect(context.Background())
		if err != nil {
			logger.Panicf("can't stop MongoDB Client -> %s", err)
		}

		// Драйвер MongoDB использует дефолтный клиент под капотом
		http.DefaultClient.CloseIdleConnections()
	}()

	if err != nil {
		logger.Panicf("can't create MongDB client -> %s", err)
	}

	iss := gomoex.NewISSClient(httpClient)

	eventBus := app.PrepareEventBus(
		logger.WithPrefix("EventBus"),
		telegramClient,
		mongoClient,
		iss,
	)

	httpServer := servers.NewHTTPServer(
		logger.WithPrefix("Server"),
		cfg.Server.Addr,
		front.NewFrontend(logger.WithPrefix("Server"), mongoClient),
		cfg.Server.Timeout,
	)

	var group errgroup.Group
	defer func() {
		err := group.Wait()
		if err != nil {
			logger.Panicf("can't stop services -> %s", err)
		}
	}()

	repo := domain.NewRepo[time.Time](mongoClient)
	tradingDatesService := data.NewTradingDateService(
		logger.WithPrefix("TradingDateService"),
		eventBus,
		repo,
		iss,
	)

	for _, s := range []func(ctx context.Context) error{
		eventBus.Run,
		tradingDatesService.Run,
		httpServer.Run,
	} {
		service := s

		group.Go(func() error {
			return service(appCtx)
		})
	}
}
