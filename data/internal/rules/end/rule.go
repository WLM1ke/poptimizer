// Package end содержит правило, порождающее события через определенные промежутки времени.
package end

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_tickerDuration = time.Minute
	_group          = "day_ended"
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45
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
	loc  *time.Location
}

// New правило окончания дня (необязательно торгового). Окончания дня привязано к моменту публикации итогов торгов.
func New(logger *lgr.Logger, timeout time.Duration) *Rule {
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time zone")
	}

	return &Rule{logger: logger, timeout: timeout, loc: loc}
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
			r.sendIfStart(out)

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

func (r *Rule) sendIfStart(out chan<- domain.Event) {
	now := time.Now().In(r.loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, r.loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	lastNew := time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)
	if r.last.Before(lastNew) {
		r.last = lastNew

		out <- domain.NewUpdateCompleted(ID, lastNew)
	}
}
