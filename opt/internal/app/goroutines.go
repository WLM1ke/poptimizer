package app

import (
	"context"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"runtime"
	"time"
)

const _goroutineInterval = time.Hour

func goroutineCounter(ctx context.Context, logger lgr.Logger) {
	ticker := time.NewTicker(_goroutineInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			logger.Infof("%d goroutines are running", runtime.NumGoroutine())
		case <-ctx.Done():
			return
		}
	}
}
