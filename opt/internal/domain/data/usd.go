package data

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

const (
	// USDGroup группа и id данных курсе доллара.
	USDGroup = "usd"

	_format = `2006-01-02`
	_ticker = `USD000UTSTOM`
)

// USD свечка с данными о курсе доллара.
type USD struct {
	Date  time.Time
	Open  float64
	Close float64
	High  float64
	Low      float64
	Turnover float64
}

// USDHandler обработчик событий, отвечающий за загрузку информации о курсе доллара.
type USDHandler struct {
	domain.Filter
	pub  domain.Publisher
	repo domain.ReadAppendRepo[Rows[USD]]
	iss  *gomoex.ISSClient
}

// NewUSDHandler создает обработчик событий, отвечающий за загрузку информации о курсе доллара.
func NewUSDHandler(
	pub domain.Publisher,
	repo domain.ReadAppendRepo[Rows[USD]],
	iss *gomoex.ISSClient,
) *USDHandler {
	return &USDHandler{
		Filter: domain.Filter{
			Sub:   Subdomain,
			Group: TradingDateGroup,
			ID:    TradingDateGroup,
		},
		iss:  iss,
		repo: repo,
		pub:  pub,
	}
}

// Handle проверят событие о возможной публикации торговых данных.
//
// Публикует событие о последней торговой дате в случае подтверждения наличия новых данных.
func (u USDHandler) Handle(ctx context.Context, event domain.Event) error {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: USDGroup,
		ID:    USDGroup,
	}

	table, err := u.repo.Get(ctx, qid)
	if err != nil {
		return err
	}

	rowsRaw, err := u.download(ctx, event, table)
	if err != nil {
		return err
	}

	rows := u.convert(rowsRaw)

	if err := u.validate(table, rows); err != nil {
		return err
	}

	if !table.Data.IsEmpty() {
		rows = rows[1:]
	}

	table.Timestamp = event.Timestamp
	table.Data = rows

	if table.Data.IsEmpty() {
		return nil
	}

	if err := u.repo.Append(ctx, table); err != nil {
		return err
	}

	u.pub.Publish(domain.Event{
		QualifiedID: qid,
		Timestamp:   event.Timestamp,
	})

	return nil
}

func (u USDHandler) download(
	ctx context.Context,
	event domain.Event,
	table domain.Entity[Rows[USD]],
) ([]gomoex.Candle, error) {
	start := ""
	if !table.Data.IsEmpty() {
		start = table.Data.LastRow().Date.Format(_format)
	}

	end := event.Timestamp.Format(_format)

	rowsRaw, err := u.iss.MarketCandles(
		ctx,
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_ticker,
		start,
		end,
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download usd data -> %w", err)
	}

	return rowsRaw, nil
}

func (u USDHandler) convert(raw []gomoex.Candle) Rows[USD] {
	rows := make(Rows[USD], 0, len(raw))

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

func (u USDHandler) validate(table domain.Entity[Rows[USD]], rows Rows[USD]) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v", prev)
	}

	if table.Data.IsEmpty() {
		return nil
	}

	if table.Data.LastRow() != rows[0] {
		return fmt.Errorf(
			"old rows %+v not match new %+v",
			table.Data.LastRow(),
			rows[0])
	}

	return nil
}
