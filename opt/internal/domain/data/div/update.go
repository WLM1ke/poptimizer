package div

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/usd"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

// Service обновления дивидендов в рублях.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	raw    domain.ReadRepo[raw.Table]
}

// NewService создает сервис для обновления дивидендов в рублях.
func NewService(logger lgr.Logger, repo domain.ReadWriteRepo[Table], rawDiv domain.ReadRepo[raw.Table]) *Service {
	return &Service{logger: logger, repo: repo, raw: rawDiv}
}

// Update обновляет дивиденды в рублях.
func (s Service) Update(ctx context.Context, date time.Time, table securities.Table, rate usd.Table) {
	defer s.logger.Infof("update is finished")

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, sec := range table {
		sec := sec

		waitGroup.Add(1)

		go func() {
			defer waitGroup.Done()

			s.updateOne(ctx, date, sec, rate)
		}()
	}
}

func (s Service) updateOne(ctx context.Context, date time.Time, sec securities.Security, rate usd.Table) {
	rawDiv, err := s.raw.Get(ctx, raw.ID(sec.Ticker))
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	if len(rawDiv.Entity()) == 0 {
		return
	}

	div, err := s.prepareDiv(rawDiv.Entity(), rate)
	if err != nil {
		s.logger.Warnf("%s %s", sec.Ticker, err)

		return
	}

	if err := s.validate(div); err != nil {
		s.logger.Warnf("%s %s", sec.Ticker, err)

		return
	}

	agg, err := s.repo.Get(ctx, ID(sec.Ticker))
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	agg.Update(div, date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s", err)

		return
	}
}

func (s Service) prepareDiv(
	rawDivs raw.Table,
	rates usd.Table,
) (dividends Table, err error) {
	var date time.Time

	for _, row := range rawDivs {
		if !row.Date.Equal(date) {
			date = row.Date

			dividends = append(dividends, Dividend{Date: date})
		}

		switch row.Currency {
		case raw.RURCurrency:
			dividends[len(dividends)-1].Value += row.Value
		case raw.USDCurrency:
			n := sort.Search(
				len(rates),
				func(i int) bool { return rates[i].Date.After(date) },
			)
			dividends[len(dividends)-1].Value += row.Value * rates[n-1].Close
		default:
			return nil, fmt.Errorf(
				"unknown currency %+v",
				row.Currency,
			)
		}
	}

	return dividends, nil
}

func (s Service) validate(div Table) error {
	prev := div[0].Date
	for _, row := range div[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v and %+v", prev, row.Date)
	}

	return nil
}
