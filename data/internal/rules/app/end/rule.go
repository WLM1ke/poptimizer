// Package end содержит правило, порождающее событие о возможной публикации торговой статистики.
package end

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_tickerDuration = time.Minute
	_group          = "day_ended"
)

// ID события окончания дня (необязательно торгового). Окончания дня привязано к моменту публикации итогов торгов.
var ID = domain.NewID(_group, _group)

// Rule - правило, сообщающее о возможном появлении новых данных.
//
// Данные события могут использоваться для запуска некоторых действий на регулярной основе.
type Rule struct {
	logger  *lgr.Logger
	timeout time.Duration

	last time.Time
}

// New правило окончания дня (необязательно торгового). Окончания дня привязано к моменту публикации итогов торгов.
func New(logger *lgr.Logger, timeout time.Duration) *Rule {
	return &Rule{logger: logger, timeout: timeout}
}

// Activate возвращает исходящий канал с событиями об окончании дня.
//
// Если это был торговый день, то была опубликована информация о результатах торгов.
func (r *Rule) Activate(inbox <-chan domain.Event) <-chan domain.Event {
	out := make(chan domain.Event)

	go func() {
		r.logger.Infof("DayEndedRule: started")
		defer r.logger.Infof("DayEndedRule: stopped")

		defer close(out)

		ticker := time.NewTicker(_tickerDuration)
		defer ticker.Stop()

		for {
			r.sendIfNewDay(out)

			select {
			case _, ok := <-inbox:
				if !ok {
					return
				}
			case <-ticker.C:
			}
		}
	}()

	return out
}

func (r *Rule) sendIfNewDay(out chan<- domain.Event) {
	lastNew := domain.LastTradingDate()
	if r.last.Before(lastNew) {
		r.last = lastNew

		out <- domain.NewUpdateCompleted(ID)
	}
}
