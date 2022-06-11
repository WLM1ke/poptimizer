package selected

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

// Group группа и идентификатор выбранных тикеров.
const Group = "selected"

// Handler обработчик событий, отвечающий за обновление информации о выбранных для анализа тикерах.
type Handler struct {
	domain.Filter
	pub  domain.Publisher
	repo domain.ReadWriteRepo[Tickers]
}

// NewHandler создает обработчик событий, отвечающий за обновление информации о выбранных тикерах.
func NewHandler(pub domain.Publisher, repo domain.ReadWriteRepo[Tickers]) *Handler {
	return &Handler{
		Filter: domain.Filter{
			Sub:   data.Subdomain,
			Group: data.SecuritiesGroup,
			ID:    data.SecuritiesGroup,
		},
		repo: repo,
		pub:  pub,
	}
}

// Handle реагирует на событие об торгуемых бумагах, и обновляет список выбранных.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	sec, ok := event.Data.(data.TableSecurities)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	event.QualifiedID = domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: Group,
		ID:    Group,
	}

	agg, err := h.repo.Get(ctx, ID())
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	agg.Timestamp = event.Timestamp
	agg.Entity = agg.Entity.update(sec)

	if err := h.repo.Save(ctx, agg); err != nil {
		event.Data = err
		h.pub.Publish(event)
	}

	event.Data = agg.Entity

	h.pub.Publish(event)
}
