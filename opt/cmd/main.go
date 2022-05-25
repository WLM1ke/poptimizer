package main

import (
	"context"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"syscall"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/bus"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/caarlos0/env/v6"
	"go.uber.org/goleak"
)

type config struct {
	App struct {
		GoroutineInterval time.Duration `envDefault:"1m"`
	}
	HTTPClient struct {
		Connections int `envDefault:"20"`
	}
	MongoDB struct {
		URI string `env:"URI,unset" envDefault:"mongodb://localhost:27017"`
		DB  string `envDefault:"data"`
	}
	Telegram struct {
		Token  string `env:"TOKEN,unset"`
		ChatID string `env:"CHAT_ID,unset"`
	}
}

func main() {
	logger := lgr.New("App")

	defer func() {
		checkLeaks(logger)

		if r := recover(); r != nil {
			logger.Warnf("stopped with exit code 1 -> %s", r)
			os.Exit(1)
		}

		logger.Infof("stopped with exit code 0")
		os.Exit(0)
	}()

	cfg := loadCfg(logger)

	httpClient := clients.NewHTTPClient(cfg.HTTPClient.Connections)
	defer httpClient.CloseIdleConnections()

	telegramClient, err := clients.NewTelegram(httpClient, cfg.Telegram.Token, cfg.Telegram.ChatID)
	if err != nil {
		logger.Panicf("can't create telegram client -> %s", err)
	}

	appCtx := createCtx(logger, cfg.App.GoroutineInterval)
	eventBus := bus.NewEventBus(logger.WithPrefix("EventBus"), telegramClient)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		data.NewDayEnded(logger.WithPrefix("DayEnded"), eventBus).Run(appCtx)
	}()

	eventBus.Run(appCtx)
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

func checkLeaks(logger *lgr.Logger) {
	if err := goleak.Find(); err != nil {
		logger.Panicf("%v", err)
	}
}
