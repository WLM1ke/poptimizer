package update

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/cpi"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/index"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/trading"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_updateTimeout  = time.Minute * 5
	_tickerDuration = time.Minute
	// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
	_issTZ      = "Europe/Moscow"
	_issHour    = 0
	_issMinute  = 45
	_timeFormat = "2006-01-02"
)

// Service - служба занимающаяся оркестрацией обновления биржевых данных.
//
// Отслеживающая окончания дня, проверяет, что день был торговым, то есть появилась новые данные об итогах торгов.
// После этого начинает обновлять остальные данные, где возможно параллельно.
type Service struct {
	logger lgr.Logger

	loc        *time.Location
	checkedDay time.Time

	tradingSrv *trading.Service

	cpiSrv   *cpi.Service
	indexSrv *index.Service

	secSrv   *securities.Service
	quoteSrv *quote.Service
}

// NewService - создает службу, обновляющую биржевые данные.
func NewService(
	logger lgr.Logger,
	tradingSrv *trading.Service,
	cpiSrv *cpi.Service,
	indexSrv *index.Service,
	secSrv *securities.Service,
	quoteSrv *quote.Service,
) (*Service, error) {
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		return nil, fmt.Errorf("can't load time MOEX zone -> %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), _updateTimeout)
	defer cancel()

	day, err := tradingSrv.Get(ctx)
	if err != nil {
		return nil, fmt.Errorf("can't load last trading date -> %w", err)
	}

	return &Service{
		logger:     logger,
		loc:        loc,
		checkedDay: day,
		tradingSrv: tradingSrv,
		cpiSrv:     cpiSrv,
		indexSrv:   indexSrv,
		secSrv:     secSrv,
		quoteSrv:   quoteSrv,
	}, nil
}

// Run запускает регулярное обновление статистики после окончания торгового дня.
func (s *Service) Run(ctx context.Context) error {
	s.logger.Infof("started with last update for %s", s.checkedDay.Format(_timeFormat))

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	for {
		s.tryToUpdate(ctx)

		select {
		case <-ctx.Done():
			s.logger.Infof("stopped with last update for %s", s.checkedDay.Format(_timeFormat))

			return nil
		case <-ticker.C:
		}
	}
}

func (s *Service) tryToUpdate(ctx context.Context) {
	lastDayEnded := s.lastDayEnded()
	if !s.checkedDay.Before(lastDayEnded) {
		return
	}

	s.logger.Infof("%s ended", lastDayEnded.Format(_timeFormat))
	s.logger.Infof("checking new trading day")

	ctx, cancel := context.WithTimeout(ctx, _updateTimeout)
	defer cancel()

	lastTradingDay, err := s.tradingSrv.Update(ctx, s.checkedDay)

	switch {
	case errors.Is(err, trading.ErrUpdateNotRequired):
		s.checkedDay = lastDayEnded
		s.logger.Infof("updates not required")

		return
	case err != nil:
		s.logger.Warnf("can't check new trading day -> %s", err)

		return
	}

	s.logger.Infof("beginning updates")
	defer s.logger.Infof("updates are finished")

	s.update(ctx, lastTradingDay)
	s.checkedDay = lastDayEnded
}

func (s *Service) lastDayEnded() time.Time {
	now := time.Now().In(s.loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, s.loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	return time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)
}

func (s *Service) update(ctx context.Context, lastTradingDay time.Time) {
	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()
		s.updateNonSec(ctx, lastTradingDay)
	}()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()
		s.updateQuote(ctx, lastTradingDay)
	}()
}

func (s *Service) updateNonSec(ctx context.Context, lastTradingDay time.Time) {
	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()
		s.cpiSrv.Update(ctx, lastTradingDay)
	}()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()
		s.indexSrv.Update(ctx, lastTradingDay)
	}()
}

func (s *Service) updateQuote(ctx context.Context, lastTradingDay time.Time) {
	sec := s.secSrv.Update(ctx, lastTradingDay)

	s.quoteSrv.Update(ctx, lastTradingDay, sec)
}
