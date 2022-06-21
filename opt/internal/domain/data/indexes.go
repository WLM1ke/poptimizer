package data

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

const _IndexesGroup = "indexes"

// IndexID - id свечек индексов.
func IndexID(index string) domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   Subdomain,
		Group: _IndexesGroup,
		ID:    index,
	}
}

// Index свечка с данными об индексе.
type Index struct {
	Date     time.Time
	Open     float64
	Close    float64
	High     float64
	Low      float64
	Turnover float64
}

// TableIndex - таблица с котировками биржевого индекса.
type TableIndex = Table[Index]

// IndexesHandler обработчик событий, отвечающий за загрузку информации об биржевых индексах.
type IndexesHandler struct {
	pub  domain.Publisher
	repo domain.ReadAppendRepo[TableIndex]
	iss  *gomoex.ISSClient
}

// NewIndexesHandler - создает обработчик событий для загрузи биржевых индексов.
func NewIndexesHandler(
	pub domain.Publisher,
	repo domain.ReadAppendRepo[TableIndex],
	iss *gomoex.ISSClient,
) *IndexesHandler {
	return &IndexesHandler{pub: pub, repo: repo, iss: iss}
}

// Match выбирает событие начала торгового дня.
func (h IndexesHandler) Match(event domain.Event) bool {
	return event.QualifiedID == TradingDateID() && event.Data == nil
}

func (h IndexesHandler) String() string {
	return "trading date -> indexes"
}

// Handle реагирует на событие об обновлении торговых дат и обновляет данные об индексах.
func (h IndexesHandler) Handle(ctx context.Context, event domain.Event) {
	var waitGroup sync.WaitGroup

	for _, index := range [4]string{`MCFTRR`, `MEOGTRR`, `IMOEX`, `RVI`} {
		waitGroup.Add(1)

		index := index

		go func() {
			defer waitGroup.Done()

			h.handleOne(ctx, IndexID(index), event)
		}()
	}

	waitGroup.Wait()
}

func (h IndexesHandler) handleOne(ctx context.Context, qid domain.QualifiedID, event domain.Event) {
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
}

func (h IndexesHandler) download(
	ctx context.Context,
	event domain.Event,
	agg domain.Aggregate[TableIndex],
) ([]gomoex.Quote, error) {
	start := ""
	if !agg.Entity.IsEmpty() {
		start = agg.Entity.LastRow().Date.Format(_ISSDateFormat)
	}

	end := event.Timestamp.Format(_ISSDateFormat)

	rowsRaw, err := h.iss.MarketHistory(
		ctx,
		gomoex.EngineStock,
		gomoex.MarketIndex,
		event.ID,
		start,
		end,
	)
	if err != nil {
		return nil, fmt.Errorf("can't download %s data -> %w", event.ID, err)
	}

	return rowsRaw, nil
}

func (h IndexesHandler) convert(raw []gomoex.Quote) TableIndex {
	rows := make(TableIndex, 0, len(raw))

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

func (h IndexesHandler) validate(agg domain.Aggregate[TableIndex], rows TableIndex) error {
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
