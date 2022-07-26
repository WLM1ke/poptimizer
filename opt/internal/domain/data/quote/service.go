package quote

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _ISSDateFormat = `2006-01-02`

// Service обновляет котировки бумаг.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	iss    *gomoex.ISSClient
}

// NewService создает сервис для загрузки котировок бумаг.
func NewService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	iss *gomoex.ISSClient,
) *Service {
	return &Service{logger: logger, repo: repo, iss: iss}
}

// Update обновляет котировки бумаг из таблицы до заданной даты.
func (s Service) Update(ctx context.Context, date time.Time, table securities.Table) {
	defer s.logger.Infof("update is finished")

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, sec := range table {
		waitGroup.Add(1)

		sec := sec

		go func() {
			defer waitGroup.Done()

			s.updateOne(ctx, date, sec)
		}()
	}
}

func (s Service) updateOne(ctx context.Context, date time.Time, sec securities.Security) {
	agg, err := s.repo.Get(ctx, ID(sec.Ticker))
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	table := agg.Entity()

	raw, err := s.download(ctx, date, sec, table)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	if len(raw) == 0 {
		return
	}

	rows := s.convert(raw)

	if err := s.validate(table, rows); err != nil {
		s.logger.Warnf("%s %s", sec.Ticker, err)

		return
	}

	if !table.IsEmpty() {
		rows = rows[1:]
	}

	if rows.IsEmpty() {
		return
	}

	agg.Update(append(table, rows...), date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s", err)

		return
	}
}

func (s Service) download(
	ctx context.Context,
	date time.Time,
	sec securities.Security,
	table Table,
) ([]gomoex.Candle, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Date.Format(_ISSDateFormat)
	}

	market := ""

	switch sec.Board {
	case gomoex.BoardTQBR, gomoex.BoardTQTF:
		market = gomoex.MarketShares
	case gomoex.BoardFQBR:
		market = gomoex.MarketForeignShares
	default:
		return nil, fmt.Errorf(
			"%s has unknown board %s",
			sec.Ticker,
			sec.Board,
		)
	}

	rows, err := s.iss.MarketCandles(
		ctx,
		gomoex.EngineStock,
		market,
		sec.Ticker,
		start,
		date.Format(_ISSDateFormat),
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download candles for %s -> %w", sec.Ticker, err)
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Begin.Before(rows[j].Begin) })

	return rows, nil
}

func (s Service) convert(raw []gomoex.Candle) Table {
	rows := make(Table, 0, len(raw))

	for _, row := range raw {
		rows = append(rows, Quote{
			Date:     row.Begin,
			Open:     row.Open,
			Close:    row.Close,
			High:     row.High,
			Low:      row.Low,
			Turnover: row.Value,
		})
	}

	return rows
}

func (s Service) validate(table, rows Table) error {
	if table.IsEmpty() {
		return nil
	}

	if table.LastRow() != rows[0] {
		return fmt.Errorf(
			"old rows %+v not match new %+v",
			table.LastRow(),
			rows[0])
	}

	return nil
}
