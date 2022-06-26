package quote

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
)

const _ISSDateFormat = `2006-01-02`

// Handler обработчик событий, отвечающий за загрузку котировок бумаг.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadAppendRepo[Table]
	iss  *gomoex.ISSClient
}

// NewHandler создает обработчик событий, загрузки котировок бумаг.
func NewHandler(
	pub domain.Publisher,
	repo domain.ReadAppendRepo[Table],
	iss *gomoex.ISSClient,
) *Handler {
	return &Handler{pub: pub, repo: repo, iss: iss}
}

// Match выбирает событие о торгуемой бумаге.
func (h Handler) Match(event domain.Event) bool {
	_, ok := event.Data.(securities.Security)

	return ok && event.QID == securities.ID(event.ID)
}

func (h Handler) String() string {
	return "security -> quotes"
}

// Handle реагирует на событие об торгуемой бумаге и обновляет ее котировки.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	qid := ID(event.ID)

	event.QID = qid

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

	if len(raw) == 0 {
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

	sec, ok := event.Data.(securities.Security)
	if !ok {
		return nil, fmt.Errorf("incorrect event payload")
	}

	market := ""

	switch sec.Board {
	case gomoex.BoardTQBR, gomoex.BoardTQTF:
		market = gomoex.MarketShares
	case gomoex.BoardFQBR:
		market = gomoex.MarketForeignShares
	default:
		return nil, fmt.Errorf(
			"unknown board %s",
			sec.Board,
		)
	}

	rows, err := h.iss.MarketCandles(
		ctx,
		gomoex.EngineStock,
		market,
		event.ID,
		start,
		end,
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download candles for %s -> %w", event.ID, err)
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Begin.Before(rows[j].Begin) })

	return rows, nil
}

func (h Handler) convert(raw []gomoex.Candle) Table {
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

func (h Handler) validate(agg domain.Aggregate[Table], rows Table) error {
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
