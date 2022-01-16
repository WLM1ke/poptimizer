package app

import (
	"context"
	"runtime"
	"time"
)

const _counterInterval = time.Hour

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
