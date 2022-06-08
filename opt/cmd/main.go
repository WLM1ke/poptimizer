package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/app"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/internal/front"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/caarlos0/env/v6"
	"go.uber.org/goleak"
	"golang.org/x/sync/errgroup"
)

type config struct {
	App struct {
		GoroutineInterval time.Duration `envDefault:"1m"`
	}
	Server struct {
		Addr           string        `envDefault:"localhost:10000"`
		RespondTimeout time.Duration `envDefault:"1s"`
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

	run(cfg, logger)
}

func atExit(logger *lgr.Logger) {
	leak := `github.com/alexedwards/scs/v2/memstore.(*MemStore).startCleanup`

	if err := goleak.Find(goleak.IgnoreTopFunction(leak)); err != nil {
		logger.Warnf("stopped with exit code 1 -> found leaked goroutines %s", err)
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

func run(cfg config, logger *lgr.Logger) {
	ctx := createCtx(logger, cfg.App.GoroutineInterval)

	httpClient := clients.NewHTTPClient(cfg.HTTPClient.Connections)
	defer httpClient.CloseIdleConnections()

	telegramClient, err := clients.NewTelegram(httpClient, cfg.Telegram.Token, cfg.Telegram.ChatID)
	if err != nil {
		logger.Panicf("can't create telegram client -> %s", err)
	}

	iss := gomoex.NewISSClient(httpClient)

	mongo, eventBus := app.PrepareEventBus(
		ctx,
		logger,
		cfg.MongoDB.URI,
		telegramClient,
		httpClient,
	)
	defer func() {
		err := mongo.Disconnect(context.Background())
		if err != nil {
			logger.Panicf("can't stop MongoDB Client -> %s", err)
		}

		// Драйвер MongoDB использует дефолтный клиент под капотом
		http.DefaultClient.CloseIdleConnections()
	}()

	tradingDatesService := data.NewTradingDateService(
		logger.WithPrefix("TradingDateService"),
		eventBus,
		domain.NewRepo[time.Time](mongo),
		iss,
	)

	httpServer := servers.NewHTTPServer(
		logger.WithPrefix("Server"),
		cfg.Server.Addr,
		front.NewFrontend(logger.WithPrefix("Server"), mongo, eventBus),
		cfg.Server.RespondTimeout,
	)

	services := []service{
		eventBus.Run,
		httpServer.Run,
		tradingDatesService.Run,
	}

	runServices(ctx, logger, services)
}

type service func(ctx context.Context) error

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

func runServices(ctx context.Context, logger *lgr.Logger, services []service) {
	var group errgroup.Group
	defer func() {
		err := group.Wait()
		if err != nil {
			logger.Panicf("can't stop services -> %s", err)
		}
	}()

	for _, s := range services {
		service := s

		group.Go(func() error { return service(ctx) })
	}
}
