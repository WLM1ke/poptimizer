package dates

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_tradingDateGroup = "trading_date"
	_timeout          = time.Second * 30

	_tickerDuration = time.Minute
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45
)

// ID - id информации о последнем торговом дне.
func ID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _tradingDateGroup,
		ID:    _tradingDateGroup,
	}
}

// Service - служба отслеживающая окончания торгового дня и рассылающая сообщение об этом.
type Service struct {
	logger *lgr.Logger
	repo   domain.ReadWriteRepo[time.Time]

	iss *gomoex.ISSClient
	loc *time.Location

	pub domain.Publisher

	checkedDate time.Time
}

// NewService - создает службу, публикующую сообщение о возможной публикации статистики.
func NewService(
	logger *lgr.Logger,
	publisher domain.Publisher,
	repo domain.ReadWriteRepo[time.Time],
	iss *gomoex.ISSClient,
) *Service {
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		logger.Panicf("can't load time MOEX zone")
	}

	return &Service{
		logger: logger,
		repo:   repo,
		iss:    iss,
		loc:    loc,
		pub:    publisher,
	}
}

// Run запускает рассылку о возможной публикации статистики после окончания торгового дня.
func (s *Service) Run(ctx context.Context) error {
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

func (s *Service) publishIfNewDay(ctx context.Context) {
	ctx, cancel := context.WithTimeout(ctx, _timeout)
	defer cancel()

	if s.checkedDate.IsZero() {
		if err := s.init(ctx); err != nil {
			s.pubErr(err)

			return
		}
	}

	if newDay, ok := s.getNewDay(time.Now()); ok {
		if err := s.update(ctx); err != nil {
			s.pubErr(err)

			return
		}

		s.checkedDate = newDay
	}
}

func (s *Service) init(ctx context.Context) error {
	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return err
	}

	s.checkedDate = agg.Entity

	return nil
}

func (s *Service) pubErr(err error) {
	event := domain.Event{
		QID:       ID(),
		Timestamp: s.checkedDate,
		Data:      err,
	}

	s.pub.Publish(event)
}

func (s *Service) getNewDay(now time.Time) (time.Time, bool) {
	now = now.In(s.loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, s.loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	newDay := time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)

	return newDay, s.checkedDate.Before(newDay)
}

func (s *Service) update(ctx context.Context) error {
	rows, err := s.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		return fmt.Errorf("cat' download trading dates -> %w", err)
	}

	if len(rows) != 1 {
		return fmt.Errorf("wrong rows count %d", len(rows))
	}

	lastTradingDate := rows[0].Till

	if !s.checkedDate.Before(lastTradingDate) {
		return nil
	}

	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return err
	}

	agg.Timestamp = lastTradingDate
	agg.Entity = lastTradingDate

	if err := s.repo.Save(ctx, agg); err != nil {
		return err
	}

	event := domain.Event{
		QID:       ID(),
		Timestamp: lastTradingDate,
	}

	s.pub.Publish(event)

	return nil
}
