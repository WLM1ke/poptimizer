package data

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

// TradingDateGroup группа и id данных о последней торговой дате.
const (
	TradingDateGroup = "trading_date"
	_timeout         = time.Second * 30

	_tickerDuration = time.Minute
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45
)

var loc = func() *time.Location { //nolint:gochecknoglobals // Загрузка зоны происходит медленно
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time MOEX zone")
	}

	return loc
}()

// TradingDateService - служба отслеживающая окончания торгового дня и рассылающая сообщение об этом.
type TradingDateService struct {
	logger *lgr.Logger
	repo   domain.ReadWriteRepo[time.Time]
	iss    *gomoex.ISSClient
	pub    domain.Publisher

	tradingDate time.Time
}

// NewTradingDateService - создает службу, публикующую сообщение о возможной публикации статистики.
func NewTradingDateService(
	logger *lgr.Logger,
	publisher domain.Publisher,
	repo domain.ReadWriteRepo[time.Time],
	iss *gomoex.ISSClient,
) *TradingDateService {
	return &TradingDateService{logger: logger, repo: repo, iss: iss, pub: publisher}
}

// Run запускает рассылку о возможной публикации статистики после окончания торгового дня.
func (s *TradingDateService) Run(ctx context.Context) error {
	s.logger.Infof("started")
	defer s.logger.Infof("stopped")

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	for {
		s.publishIfNewDay(ctx)

		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}

func (s *TradingDateService) publishIfNewDay(ctx context.Context) {
	newTradingDate := lastTradingDate()

	if !s.tradingDate.Before(newTradingDate) {
		return
	}

	event := domain.Event{
		QualifiedID: domain.QualifiedID{
			Sub:   Subdomain,
			Group: TradingDateGroup,
			ID:    TradingDateGroup,
		},
		Timestamp: newTradingDate,
	}

	newTradingDate, err := s.getTradingDate(ctx)
	if err != nil {
		event.Data = err
		s.pub.Publish(event)

		return
	}

	if !s.tradingDate.Before(newTradingDate) {
		return
	}

	s.tradingDate = newTradingDate
	event.Timestamp = newTradingDate

	s.pub.Publish(event)
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

func (s *TradingDateService) getTradingDate(ctx context.Context) (date time.Time, err error) {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: TradingDateGroup,
		ID:    TradingDateGroup,
	}

	ctx, cancel := context.WithTimeout(ctx, _timeout)
	defer cancel()

	table, err := s.repo.Get(ctx, qid)
	if err != nil {
		return date, err
	}

	rows, err := s.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		return date, err
	}

	if len(rows) != 1 {
		return date, fmt.Errorf("wrong rows count %d", len(rows))
	}

	newDate := rows[0].Till
	if !newDate.After(table.Timestamp) {
		return date, nil
	}

	table.Timestamp = newDate
	table.Entity = newDate

	if err := s.repo.Save(ctx, table); err != nil {
		return date, err
	}

	return newDate, nil
}
