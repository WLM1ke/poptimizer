package usd

import (
	"context"
	"fmt"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/dates"
)

const (
	_ISSDateFormat = `2006-01-02`
	_usdTicker     = `USD000UTSTOM`
)

// Handler обработчик событий, отвечающий за загрузку информации о курсе доллара.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadAppendRepo[Table]
	iss  *gomoex.ISSClient
}

// NewHandler создает обработчик событий, отвечающий за загрузку информации о курсе доллара.
func NewHandler(
	pub domain.Publisher,
	repo domain.ReadAppendRepo[Table],
	iss *gomoex.ISSClient,
) *Handler {
	return &Handler{
		iss:  iss,
		repo: repo,
		pub:  pub,
	}
}

// Match выбирает событие начала торгового дня.
func (h Handler) Match(event domain.Event) bool {
	return event.QualifiedID == dates.ID() && event.Data == nil
}

func (h Handler) String() string {
	return "trading date -> usd"
}

// Handle реагирует на событие об обновлении торговых дат и обновляет курс.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	qid := ID()

	event.QualifiedID = qid

	agg, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	raw, err := h.download(ctx, event, agg)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	rows := h.convert(raw)

	if err := h.validate(agg, rows); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if !agg.Entity.IsEmpty() {
		rows = rows[1:]
	}

	if rows.IsEmpty() {
		return
	}

	agg.Timestamp = event.Timestamp
	agg.Entity = rows

	if err := h.repo.Append(ctx, agg); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	event.Data = agg.Entity

	h.pub.Publish(event)
}

func (h Handler) download(
	ctx context.Context,
	event domain.Event,
	agg domain.Aggregate[Table],
) ([]gomoex.Candle, error) {
	start := ""
	if !agg.Entity.IsEmpty() {
		start = agg.Entity.LastRow().Date.Format(_ISSDateFormat)
	}

	end := event.Timestamp.Format(_ISSDateFormat)

	rowsRaw, err := h.iss.MarketCandles(
		ctx,
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		start,
		end,
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download usd data -> %w", err)
	}

	return rowsRaw, nil
}

func (h Handler) convert(raw []gomoex.Candle) Table {
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

func (h Handler) validate(agg domain.Aggregate[Table], rows Table) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v", prev)
	}

	if agg.Entity.IsEmpty() {
		return nil
	}

	if agg.Entity.LastRow() != rows[0] {
		return fmt.Errorf(
			"old rows %+v not match new %+v",
			agg.Entity.LastRow(),
			rows[0])
	}

	return nil
}
