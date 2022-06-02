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
func (h TradingDateHandler) Handle(ctx context.Context, _ domain.Event) error {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: TradingDateGroup,
		ID:    TradingDateGroup,
	}

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		return err
	}

	rows, err := h.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		return fmt.Errorf("can't download trading dates info -> %w", err)
	}

	if len(rows) != 1 {
		return fmt.Errorf("wrong rows count %d", len(rows))
	}

	date := rows[0].Till
	if !date.After(table.Entity) {
		return nil
	}

	table.Entity = date
	table.Timestamp = date

	if err := h.repo.Save(ctx, table); err != nil {
		return err
	}

	h.pub.Publish(domain.Event{
		QualifiedID: qid,
		Timestamp:   date,
	})

	return nil
}
