package index

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _ISSDateFormat = `2006-01-02`

// Service загружает информацию о биржевых индексах.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	iss    *gomoex.ISSClient
}

// NewService загрузчик биржевых индексов.
func NewService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	iss *gomoex.ISSClient,
) *Service {
	return &Service{logger: logger, repo: repo, iss: iss}
}

// Update обновляет данные по индексам.
func (s Service) Update(ctx context.Context, date time.Time) {
	defer s.logger.Infof("update is finished")

	var waitGroup sync.WaitGroup

	for _, index := range [4]string{`MCFTRR`, `MEOGTRR`, `IMOEX`, `RVI`} {
		waitGroup.Add(1)

		index := index

		go func() {
			defer waitGroup.Done()

			s.handleOne(ctx, ID(index), date)
		}()
	}

	waitGroup.Wait()
}

func (s Service) handleOne(ctx context.Context, qid domain.QID, date time.Time) {
	agg, err := s.repo.Get(ctx, qid)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	table := agg.Entity()

	raw, err := s.download(ctx, qid.ID, date.Format(_ISSDateFormat), table)
	if err != nil {
		s.logger.Warnf("%s %s", qid, err)

		return
	}

	rows := s.convert(raw)

	if err := s.validate(table, rows); err != nil {
		s.logger.Warnf("%s %s", qid, err)

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
	index string,
	end string,
	table Table,
) ([]gomoex.Quote, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Date.Format(_ISSDateFormat)
	}

	rowsRaw, err := s.iss.MarketHistory(
		ctx,
		gomoex.EngineStock,
		gomoex.MarketIndex,
		index,
		start,
		end,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download %s -> %w", index, err)
	}

	return rowsRaw, nil
}

func (s Service) convert(raw []gomoex.Quote) Table {
	rows := make(Table, 0, len(raw))

	for _, row := range raw {
		rows = append(rows, Index{
			Date:     row.Date,
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
