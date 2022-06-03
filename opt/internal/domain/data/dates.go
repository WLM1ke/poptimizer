package data

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// TradingDateGroup группа и id данных о последней торговой дате.
const TradingDateGroup = "trading_date"

// TradingDateHandler обработчик событий, отвечающий за загрузку информации о последней торговой дате.
type TradingDateHandler struct {
	domain.Filter
	pub  domain.Publisher
	repo domain.ReadWriteRepo[time.Time]
	iss  *gomoex.ISSClient
}

// NewTradingDateHandler создает обработчик событий о последней торговой дате.
func NewTradingDateHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[time.Time],
	iss *gomoex.ISSClient,
) *TradingDateHandler {
	return &TradingDateHandler{
		Filter: domain.Filter{
			Sub:   Subdomain,
			Group: CheckDataGroup,
			ID:    CheckDataGroup,
		},
		iss:  iss,
		repo: repo,
		pub:  pub,
	}
}

// Handle проверят событие о возможной публикации торговых данных.
//
// Публикует событие о последней торговой дате в случае подтверждения наличия новых данных.
func (h TradingDateHandler) Handle(ctx context.Context, event domain.Event) {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: TradingDateGroup,
		ID:    TradingDateGroup,
	}

	event.QualifiedID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)
	}

	rows, err := h.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		event.Data = fmt.Errorf("can't download trading dates info -> %w", err)
		h.pub.Publish(event)
	}

	if len(rows) != 1 {
		event.Data = fmt.Errorf("wrong rows count %d", len(rows))
		h.pub.Publish(event)
	}

	date := rows[0].Till
	if !date.After(table.Entity) {
		return
	}

	table.Entity = date
	table.Timestamp = date

	if err := h.repo.Save(ctx, table); err != nil {
		event.Data = err
		h.pub.Publish(event)
	}

	event.Timestamp = date
	h.pub.Publish(event)
}
