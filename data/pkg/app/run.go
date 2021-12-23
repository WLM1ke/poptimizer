package app

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"golang.org/x/sync/errgroup"
)

// Service представляет компоненту приложения.
type Service interface {
	// Run запускает службу в блокирующем режиме с отменой по завершению контекста.
	Run(context.Context) error
}

// Run создает контекст приложения, запускает отдельные службы в рамках него и останавливает их по системному сигналу.
func Run(logger *lgr.Logger, services ...Service) {
	logger.Infof("App: starting")

	code := 0

	defer func() {
		logger.Infof("App: stopped with exit code %d", code)
		os.Exit(code)
	}()

	group, ctx := errgroup.WithContext(appCtx(logger))

	for _, service := range services {
		service := service

		group.Go(func() error {
			name := shortType(service)

			logger.Infof("%s: started", name)
			defer logger.Infof("%s: stopped", name)

			return service.Run(ctx) //nolint:wrapcheck
		})
	}

	if err := group.Wait(); err != nil {
		logger.Warnf("App: error during stopping services %s", err)

		code = 1
	}
}

func appCtx(logger *lgr.Logger) context.Context {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-ctx.Done()
		logger.Infof("App: shutdown signal received")
		cancel()
	}()

	return ctx
}

func shortType(value interface{}) string {
	parts := strings.Split(fmt.Sprintf("%T", value), ".")

	return parts[len(parts)-1]
}
