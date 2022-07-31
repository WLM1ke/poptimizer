package update

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/cpi"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/div"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/index"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/trading"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/usd"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/port"
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

// Service - служба занимающаяся оркестрацией обновления данных.
//
// Постоянно отслеживается окончание дня и в случае окончания проверяется, что он был торговым, то есть появилась новые
// данные об итогах торгов. После этого начинает обновлять остальные данные, где возможно параллельно. Если на каком-то
// шаге возникают ошибки, то они логируются, но процесс обновления продолжается, если это возможно.
//
// Дополнительно осуществляется проверка актуальности дивидендов, развертывание пользовательских данных по умолчанию при
// первом запуске и бекап их обновлений.
type Service struct {
	logger lgr.Logger

	loc        *time.Location
	checkedDay time.Time

	backupSrv domain.BackupRestore

	tradingSrv *trading.Service

	cpiSrv   *cpi.Service
	indexSrv *index.Service

	secSrv   *securities.Service
	usdSrv   *usd.Service
	divSrv   *div.Service
	quoteSrv *quote.Service

	statusSrv   *raw.StatusService
	reestrySrv  *raw.ReestryService
	nasdaqSrv   *raw.NASDAQService
	checkRawSrv *raw.CheckRawService

	portSrv *port.Service
}

// NewService - создает службу, обновляющую биржевые данные.
func NewService(
	logger lgr.Logger,
	backupSrv domain.BackupRestore,
	tradingSrv *trading.Service,
	cpiSrv *cpi.Service,
	indexSrv *index.Service,
	secSrv *securities.Service,
	usdSrv *usd.Service,
	divSrv *div.Service,
	quoteSrv *quote.Service,
	statusSrv *raw.StatusService,
	reestrySrv *raw.ReestryService,
	nasdaqSrv *raw.NASDAQService,
	checkRawSrv *raw.CheckRawService,
	portSrv *port.Service,
) (*Service, error) {
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		return nil, fmt.Errorf("can't load time MOEX zone -> %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), _updateTimeout)
	defer cancel()

	if count, err := backupSrv.Restore(ctx, data.Subdomain, securities.ID().Group); err != nil {
		return nil, err
	} else if count == 0 {
		logger.Infof("selected securities restored")
	}

	if count, err := backupSrv.Restore(ctx, data.Subdomain, raw.ID("").Group); err != nil {
		return nil, err
	} else if count == 0 {
		logger.Infof("raw dividends restored")
	}

	day, err := tradingSrv.Get(ctx)
	if err != nil {
		return nil, fmt.Errorf("can't load last trading date -> %w", err)
	}

	return &Service{
		logger:      logger,
		loc:         loc,
		checkedDay:  day,
		backupSrv:   backupSrv,
		tradingSrv:  tradingSrv,
		cpiSrv:      cpiSrv,
		indexSrv:    indexSrv,
		secSrv:      secSrv,
		usdSrv:      usdSrv,
		divSrv:      divSrv,
		quoteSrv:    quoteSrv,
		statusSrv:   statusSrv,
		reestrySrv:  reestrySrv,
		nasdaqSrv:   nasdaqSrv,
		checkRawSrv: checkRawSrv,
		portSrv:     portSrv,
	}, nil
}

// Run запускает регулярное обновление статистики после окончания торгового дня.
func (s *Service) Run(ctx context.Context) {
	s.logger.Infof("started with last update for %s", s.checkedDay.Format(_timeFormat))

	ticker := time.NewTicker(_tickerDuration)
	defer ticker.Stop()

	for {
		s.tryToUpdate(ctx)

		select {
		case <-ctx.Done():
			s.logger.Infof("stopped with last update for %s", s.checkedDay.Format(_timeFormat))

			return
		case <-ticker.C:
		}
	}
}

func (s *Service) tryToUpdate(ctx context.Context) {
	lastDayEnded := s.lastDayEnded(time.Now())
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

func (s *Service) lastDayEnded(now time.Time) time.Time {
	now = now.In(s.loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, s.loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	return time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)
}

func (s *Service) update(ctx context.Context, lastTradingDay time.Time) {
	s.updateData(ctx, lastTradingDay)
	s.portSrv.Update(ctx)
}

func (s *Service) updateData(ctx context.Context, lastTradingDay time.Time) {
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

		s.updateSec(ctx, lastTradingDay)
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

func (s *Service) updateSec(ctx context.Context, lastTradingDay time.Time) {
	secChan := make(chan securities.Table, 1)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		s.updateDiv(ctx, lastTradingDay, secChan)
	}()

	sec := s.secSrv.Update(ctx, lastTradingDay)
	secChan <- sec
	close(secChan)

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		err := s.backupSrv.Backup(ctx, data.Subdomain, securities.ID().Group)
		if err != nil {
			s.logger.Warnf("%s", err)

			return
		}

		s.logger.Infof("backup of selected securities completed")
	}()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		s.quoteSrv.Update(ctx, lastTradingDay, sec)
	}()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		s.updateRawDiv(ctx, lastTradingDay, sec)
	}()
}

func (s *Service) updateDiv(
	ctx context.Context,
	lastTradingDay time.Time,
	secChan <-chan securities.Table,
) {
	rates := s.usdSrv.Update(ctx, lastTradingDay)

	if rates == nil {
		return
	}

	s.divSrv.Update(ctx, lastTradingDay, <-secChan, rates)
}

func (s *Service) updateRawDiv(ctx context.Context, lastTradingDay time.Time, sec securities.Table) {
	status := s.statusSrv.Update(ctx, lastTradingDay, sec)
	status = s.checkRawSrv.Check(ctx, status)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		s.reestrySrv.Update(ctx, lastTradingDay, status)
	}()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		s.nasdaqSrv.Update(ctx, lastTradingDay, status)
	}()
}
