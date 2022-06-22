package securities

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/usd"
)

// Handler обработчик событий, отвечающий за загрузку информации о торгуемых бумагах.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadWriteRepo[Table]
	iss  *gomoex.ISSClient
}

// NewHandler создает обработчик событий, отвечающий за загрузку информации о торгуемых бумагах.
func NewHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[Table],
	iss *gomoex.ISSClient,
) *Handler {
	return &Handler{
		iss:  iss,
		repo: repo,
		pub:  pub,
	}
}

// Match выбирает событие обновления курса доллара.
func (h Handler) Match(event domain.Event) bool {
	return event.QualifiedID == usd.ID() && event.Data == nil
}

func (h Handler) String() string {
	return "usd -> securities"
}

// Handle реагирует на событие об обновлении курса и обновляет данные о торгуемых бумагах.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	qid := GroupID()

	event.QualifiedID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	raw, err := h.download(ctx)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	table.Timestamp = event.Timestamp
	table.Entity = table.Entity.update(raw)

	if err := h.repo.Save(ctx, table); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	h.publish(table)
}

func (h Handler) download(
	ctx context.Context,
) (rows []gomoex.Security, err error) {
	marketsBoards := []struct {
		market string
		board  string
	}{
		{gomoex.MarketShares, gomoex.BoardTQBR},
		{gomoex.MarketShares, gomoex.BoardTQTF},
		{gomoex.MarketForeignShares, gomoex.BoardFQBR},
	}

	for _, mb := range marketsBoards {
		candles, err := h.iss.BoardSecurities(ctx, gomoex.EngineStock, mb.market, mb.board)
		if err != nil {
			return nil, fmt.Errorf(
				"can't download securities data -> %w",
				err,
			)
		}

		rows = append(rows, candles...)
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Ticker < rows[j].Ticker })

	return rows, nil
}

func (h Handler) publish(agg domain.Aggregate[Table]) {
	h.pub.Publish(domain.Event{
		QualifiedID: GroupID(),
		Timestamp:   agg.Timestamp,
		Data:        agg.Entity,
	})

	for _, sec := range agg.Entity {
		h.pub.Publish(domain.Event{
			QualifiedID: ID(sec.Ticker),
			Timestamp:   agg.Timestamp,
			Data:        sec,
		})
	}
}
