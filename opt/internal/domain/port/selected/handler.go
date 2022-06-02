package selected

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const _group = "selected"

// Handler обработчик событий, отвечающий за обновление информации о выбранных для анализа тикерах.
type Handler struct {
	domain.Filter
	repo domain.ReadWriteRepo[Tickers]
}

// NewHandler создает обработчик событий, отвечающий за обновление информации о выбранных тикерах.
func NewHandler(
	repo domain.ReadWriteRepo[Tickers],
) *Handler {
	return &Handler{
		Filter: domain.Filter{
			Sub:   data.Subdomain,
			Group: data.SecuritiesGroup,
			ID:    data.SecuritiesGroup,
		},
		repo: repo,
	}
}

// Handle реагирует на событие об торгуемых бумагах, и обновляет список выбранных.
func (h Handler) Handle(ctx context.Context, event domain.Event) error {
	agg, err := h.repo.Get(ctx, ID())
	if err != nil {
		return err
	}

	sec, ok := event.Data.(data.Rows[data.Security])
	if !ok {
		return fmt.Errorf("can't parse event data %s", event)
	}

	agg.Timestamp = event.Timestamp
	agg.Entity = agg.Entity.update(sec)

	if err := h.repo.Save(ctx, agg); err != nil {
		return err
	}

	return nil
}
