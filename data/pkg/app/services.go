package app

import (
	"context"
	"golang.org/x/sync/errgroup"
	"os/signal"
	"syscall"
)

func (a *App) runServices() {

	group, ctx := errgroup.WithContext(a.ctx())

	group.Go(func() error {
		return a.goroutineCounter(ctx)
	})

	for _, service := range a.services {
		service := service

		group.Go(func() error {
			name := shortType(service)

			a.logger.Infof("%s: started", name)
			defer a.logger.Infof("%s: stopped", name)

			return service.Run(ctx) //nolint:wrapcheck
		})
	}

	if err := group.Wait(); err != nil {
		a.code = 1
		a.logger.Warnf("App: error during stopping services -> %s", err)
	}
}

func (a *App) ctx() context.Context {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-ctx.Done()
		a.logger.Infof("App: shutdown signal received")
		cancel()
	}()

	return ctx
}
