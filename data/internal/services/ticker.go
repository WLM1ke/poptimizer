package services

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"time"
)

const (
	_tickerDuration = time.Minute
	_services       = "services"
	_ticker         = "ticker"
)

var id = domain.NewId(_services, _ticker)

// TickerRule - правило, порождающее периодические события.
//
// Данные события могут использоваться для запуска некоторых действий на регулярной основе
type TickerRule struct {
	logger *lgr.Logger
	ticker *time.Ticker
}

func NewTickerRule(logger *lgr.Logger) *TickerRule {
	return &TickerRule{logger: logger, ticker: time.NewTicker(_tickerDuration)}
}

func (t TickerRule) Activate(in <-chan domain.Event, out chan<- domain.Event) {
	t.logger.Infof("TickerRule: started")
	defer t.logger.Infof("TickerRule: stopped")
	defer t.ticker.Stop()

	out <- domain.NewVersion(id, time.Now())

	for {
		select {
		case _, ok := <-in:
			if !ok {
				return
			}
		case now := <-t.ticker.C:
			out <- domain.NewVersion(id, now)
		}
	}
}
