package app

import (
	"context"
	"fmt"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	"golang.org/x/sync/errgroup"
)

const _counterInterval = time.Hour

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

			err := service.Run(ctx)
			if err != nil {
				return fmt.Errorf("app error in service %s -> %w", name, err)
			}

			return nil
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

func (a *App) goroutineCounter(ctx context.Context) error {
	ticker := time.NewTicker(_counterInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			a.logger.Infof("App: %d goroutines are running", runtime.NumGoroutine())
		case <-ctx.Done():
			return nil
		}
	}
}
