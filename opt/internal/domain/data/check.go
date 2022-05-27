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

	// CheckDataGroup группа и id события о возможной публикации данных за новый торговый день.
	CheckDataGroup = `check_data`
)

var loc = func() *time.Location { //nolint:gochecknoglobals // Загрузка зоны происходит медленно
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time MOEX zone")
	}

	return loc
}()

// CheckData - служба отслеживающая окончания торгового дня и рассылающая сообщение об этом.
type CheckData struct {
	logger    *lgr.Logger
	last      time.Time
	publisher domain.Publisher
}

// NewCheckDataService - создает службу, публикующую сообщение о возможной публикации статистики.
func NewCheckDataService(logger *lgr.Logger, publisher domain.Publisher) *CheckData {
	return &CheckData{logger: logger, publisher: publisher}
}

// Run запускает рассылку о возможной публикации статистики после окончания торгового дня.
func (c *CheckData) Run(ctx context.Context) {
	c.logger.Infof("started")
	defer c.logger.Infof("stopped")

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	for {
		c.publishIfNewDay()

		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (c *CheckData) publishIfNewDay() {
	if lastNew := lastTradingDate(); c.last.Before(lastNew) {
		c.last = lastNew

		event := domain.Event{
			QualifiedID: domain.QualifiedID{
				Sub:   Subdomain,
				Group: CheckDataGroup,
				ID:    CheckDataGroup,
			},
			Timestamp: lastNew,
		}

		c.publisher.Publish(event)
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
