package usd

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_ISSDateFormat = `2006-01-02`
	_usdTicker     = `USD000UTSTOM`
)

// MarketCandler интерфейс API для получения свечек.
type MarketCandler interface {
	MarketCandles(
		ctx context.Context,
		engine string,
		market string,
		security string,
		from, till string,
		interval int) ([]gomoex.Candle, error)
}

// Service обновления информации о курсе доллара.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	iss    MarketCandler
}

// NewService создает службу, отвечающую за загрузку информации о курсе доллара.
func NewService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	iss MarketCandler,
) *Service {
	return &Service{
		logger: logger,
		iss:    iss,
		repo:   repo,
	}
}

// Update обновляет свечки курса доллара.
func (s Service) Update(ctx context.Context, date time.Time) Table {
	defer s.logger.Infof("update is finished")

	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	table := agg.Entity()

	raw, err := s.download(ctx, date, table)
	if err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	rows := convert(raw)

	if err := validate(table, rows); err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	if !table.IsEmpty() {
		rows = rows[1:]
	}

	if rows.IsEmpty() {
		return table
	}

	table = append(table, rows...)

	agg.Update(table, date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	return table
}

func (s Service) download(
	ctx context.Context,
	date time.Time,
	table Table,
) ([]gomoex.Candle, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Date.Format(_ISSDateFormat)
	}

	rowsRaw, err := s.iss.MarketCandles(
		ctx,
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		start,
		date.Format(_ISSDateFormat),
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download data -> %w", err)
	}

	return rowsRaw, nil
}

func convert(raw []gomoex.Candle) Table {
	rows := make(Table, 0, len(raw))

	for _, row := range raw {
		rows = append(rows, USD{
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

func validate(table, rows Table) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v", prev)
	}

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
