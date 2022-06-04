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
	Date     time.Time
	Open     float64
	Close    float64
	High     float64
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

// Handle реагирует на событие об обновлении курса и обновляет его.
func (h USDHandler) Handle(ctx context.Context, event domain.Event) {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: USDGroup,
		ID:    USDGroup,
	}

	event.QualifiedID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	raw, err := h.download(ctx, event, table)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	rows := h.convert(raw)

	if err := h.validate(table, rows); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if !table.Entity.IsEmpty() {
		rows = rows[1:]
	}

	if rows.IsEmpty() {
		return
	}

	table.Timestamp = event.Timestamp
	table.Entity = rows

	if err := h.repo.Append(ctx, table); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	h.pub.Publish(event)
}

func (h USDHandler) download(
	ctx context.Context,
	event domain.Event,
	table domain.Aggregate[Rows[USD]],
) ([]gomoex.Candle, error) {
	start := ""
	if !table.Entity.IsEmpty() {
		start = table.Entity.LastRow().Date.Format(_format)
	}

	end := event.Timestamp.Format(_format)

	rowsRaw, err := h.iss.MarketCandles(
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

func (h USDHandler) convert(raw []gomoex.Candle) Rows[USD] {
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

func (h USDHandler) validate(table domain.Aggregate[Rows[USD]], rows Rows[USD]) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v", prev)
	}

	if table.Entity.IsEmpty() {
		return nil
	}

	if table.Entity.LastRow() != rows[0] {
		return fmt.Errorf(
			"old rows %+v not match new %+v",
			table.Entity.LastRow(),
			rows[0])
	}

	return nil
}
