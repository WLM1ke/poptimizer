package data

import (
	"context"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_tickerDuration = time.Minute
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45

	BoundedCtx = `data`
	DayEndedID = `day_ended`
)

var loc = func() *time.Location { //nolint:gochecknoglobals // Загрузка зоны происходит медленно
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time MOEX zone")
	}

	return loc
}()

type DayEnded struct {
	logger    *lgr.Logger
	last      time.Time
	publisher domain.Publisher
}

func NewDayEnded(logger *lgr.Logger, publisher domain.Publisher) *DayEnded {
	return &DayEnded{logger: logger, publisher: publisher}
}

func (r *DayEnded) Run(ctx context.Context) {
	r.logger.Infof("started")
	defer r.logger.Infof("stopped")

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	for {
		r.publishIfNewDay()

		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (r *DayEnded) publishIfNewDay() {
	if lastNew := lastTradingDate(); r.last.Before(lastNew) {
		r.last = lastNew

		event := domain.Event{
			QualifiedID: domain.QualifiedID{
				BoundedCtx: BoundedCtx,
				Aggregate:  DayEndedID,
				ID:         DayEndedID,
			},
			Timestamp: lastNew,
		}

		r.publisher.Publish(event)
	}
}

func lastTradingDate() time.Time {
	now := time.Now().In(loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	return time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)
}
