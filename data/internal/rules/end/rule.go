// Package end содержит правило, порождающее события через определенные промежутки времени.
package end

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"time"
)

const (
	_tickerDuration = time.Minute
	_group          = "day_ended"
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45
)

var ID = domain.NewId(_group, _group)

// Rule - правило, сообщающее о возможном появлении новых данных.
//
// Данные события могут использоваться для запуска некоторых действий на регулярной основе
type Rule struct {
	logger *lgr.Logger

	last time.Time
	loc  *time.Location
}

func New(logger *lgr.Logger) *Rule {
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time zone")
	}

	return &Rule{logger: logger, loc: loc}
}

func (r *Rule) Activate(in <-chan domain.Event, out chan<- domain.Event) {
	r.logger.Infof("DayEndedRule: started")
	defer r.logger.Infof("DayEndedRule: stopped")

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	r.sendIfStart(out)

	for {
		select {
		case _, ok := <-in:
			if !ok {
				return
			}
		case <-ticker.C:
			r.sendIfStart(out)
		}
	}
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

		out <- domain.NewUpdateCompletedFromID(ID, lastNew)
	}
}
