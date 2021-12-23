package app

import (
	"context"
	"runtime"
	"time"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const _logInterval = time.Minute

// GoroutineCounter - сервис, который выводит текуще количество горутин.
type GoroutineCounter struct {
	logger *lgr.Logger
}

// NewGoroutineCounter - счетчик горутин, которые пишет в логи их количество.
func NewGoroutineCounter(logger *lgr.Logger) *GoroutineCounter {
	return &GoroutineCounter{logger: logger}
}

// Run - запускает сервис.
func (g GoroutineCounter) Run(ctx context.Context) error {
	ticker := time.NewTicker(_logInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			g.logger.Infof("GoroutineCounter: %d is running", runtime.NumGoroutine())
		case <-ctx.Done():
			return nil
		}
	}
}
