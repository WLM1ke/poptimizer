// Package timer содержит правило, порождающее события через определенные промежутки времени.
package timer

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

// Rule - правило, порождающее периодические события.
//
// Данные события могут использоваться для запуска некоторых действий на регулярной основе
type Rule struct {
	logger *lgr.Logger
	ticker *time.Ticker
}

func New(logger *lgr.Logger) *Rule {
	return &Rule{logger: logger, ticker: time.NewTicker(_tickerDuration)}
}

func (t Rule) Activate(in <-chan domain.Event, out chan<- domain.Event) {
	t.logger.Infof("TimerRule: started")
	defer t.logger.Infof("TimerRule: stopped")
	defer t.ticker.Stop()

	out <- domain.NewUpdateCompletedFromID(id, time.Now())

	for {
		select {
		case _, ok := <-in:
			if !ok {
				return
			}
		case now := <-t.ticker.C:
			out <- domain.NewUpdateCompletedFromID(id, now)
		}
	}
}
