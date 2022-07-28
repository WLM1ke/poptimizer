package trading

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// ErrUpdateNotRequired - отсутствуют новые данные на MOEX ISS.
var ErrUpdateNotRequired = errors.New("update not required")

// Service - служба обновляющая окончание торгового дня.
type Service struct {
	repo domain.ReadWriteRepo[Date]
	iss  *gomoex.ISSClient
}

// NewService - создает службу, публикующую сообщение о возможной публикации статистики.
func NewService(
	repo domain.ReadWriteRepo[Date],
	iss *gomoex.ISSClient,
) *Service {
	return &Service{
		repo: repo,
		iss:  iss,
	}
}

// Get предоставляет дату последнего обновления.
func (s *Service) Get(ctx context.Context) (Date, error) {
	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return Date{}, err
	}

	return agg.Entity(), nil
}

// Update обновляет данные о торговых днях.
//
// В случае появления новой информации, возвращает последнюю торговую дату.
// При отсутствии новых данных возвращается ошибка ErrUpdateNotRequired.
// При сбое во время обновления, соответсвующая ошибка.
func (s *Service) Update(ctx context.Context, lastDay time.Time) (time.Time, error) {
	table, err := s.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		return time.Time{}, fmt.Errorf("can't download trading dates -> %w", err)
	}

	if len(table) != 1 {
		return time.Time{}, fmt.Errorf("wrong rows count %d", len(table))
	}

	lastTradingDate := table[0].Till

	if !lastDay.Before(lastTradingDate) {
		return time.Time{}, ErrUpdateNotRequired
	}

	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return time.Time{}, err
	}

	agg.Update(lastTradingDate, lastTradingDate)

	if err := s.repo.Save(ctx, agg); err != nil {
		return time.Time{}, err
	}

	return lastTradingDate, nil
}
