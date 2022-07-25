package main

import (
	"context"
	"go.uber.org/goleak"
	"os"
	"os/signal"
	"syscall"

	"github.com/WLM1ke/poptimizer/opt/internal/app"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

func main() {
	logger, ctx := prepareLoggerAndCtx()

	defer atExit(logger)

	app.New(logger).Run(ctx)
}

func prepareLoggerAndCtx() (lgr.Logger, context.Context) {
	logger := lgr.New("App")
	ctx, appCancel := context.WithCancel(context.Background())

	go func() {
		defer appCancel()

		ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
		defer cancel()

		<-ctx.Done()

		logger.Infof("shutdown signal received")
	}()

	return logger, ctx
}

func atExit(logger lgr.Logger) {
	if r := recover(); r != nil {
		logger.Warnf("stopped with exit code 1 -> %s", r)
		os.Exit(1)
	}

	if err := goleak.Find(); err != nil {
		logger.Warnf("stopped with exit code 1 -> found leaked goroutines %s", err)
		os.Exit(1)
	}

	logger.Infof("stopped with exit code 0")
	os.Exit(0)
}
