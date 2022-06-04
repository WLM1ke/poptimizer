package data

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// SecuritiesGroup группа и id данных о торгуемых бумагах.
const SecuritiesGroup = "securities"

// Security описание бумаги.
type Security struct {
	Ticker     string
	Lot        int
	ISIN       string
	Board      string
	Type       string
	Instrument string
}

// SecuritiesHandler обработчик событий, отвечающий за загрузку информации о торгуемых бумагах.
type SecuritiesHandler struct {
	domain.Filter
	pub  domain.Publisher
	repo domain.ReadWriteRepo[Rows[Security]]
	iss  *gomoex.ISSClient
}

// NewSecuritiesHandler создает обработчик событий, отвечающий за загрузку информации о торгуемых бумагах.
func NewSecuritiesHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[Rows[Security]],
	iss *gomoex.ISSClient,
) *SecuritiesHandler {
	return &SecuritiesHandler{
		Filter: domain.Filter{
			Sub:   Subdomain,
			Group: USDGroup,
			ID:    USDGroup,
		},
		iss:  iss,
		repo: repo,
		pub:  pub,
	}
}

// Handle реагирует на событие об обновлении курса и обновляет данные о торгуемых бумагах.
//
// Рассылает отдельные события для каждой торгуемой бумаги.
func (h SecuritiesHandler) Handle(ctx context.Context, event domain.Event) {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: SecuritiesGroup,
		ID:    SecuritiesGroup,
	}

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

	rows := h.convert(raw)

	table.Timestamp = event.Timestamp
	table.Entity = rows

	if err := h.repo.Save(ctx, table); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	h.publish(table)
}

func (h SecuritiesHandler) download(
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

func (h SecuritiesHandler) convert(raw []gomoex.Security) Rows[Security] {
	rows := make(Rows[Security], 0, len(raw))

	for _, row := range raw {
		rows = append(rows, Security{
			Ticker:     row.Ticker,
			Lot:        row.LotSize,
			ISIN:       row.ISIN,
			Board:      row.Board,
			Type:       row.Type,
			Instrument: row.Instrument,
		})
	}

	return rows
}

func (h SecuritiesHandler) publish(table domain.Aggregate[Rows[Security]]) {
	for _, sec := range table.Entity {
		h.pub.Publish(domain.Event{
			QualifiedID: domain.QualifiedID{
				Sub:   Subdomain,
				Group: SecuritiesGroup,
				ID:    sec.Ticker,
			},
			Timestamp: table.Timestamp,
			Data:      sec,
		})
	}

	h.pub.Publish(domain.Event{
		QualifiedID: domain.QualifiedID{
			Sub:   Subdomain,
			Group: SecuritiesGroup,
			ID:    SecuritiesGroup,
		},
		Timestamp: table.Timestamp,
		Data:      table.Entity,
	})
}
