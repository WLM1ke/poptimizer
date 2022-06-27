package port

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

// Handler обработчик событий, отвечающий за обновление перечня выбранных бумаг и размеров лота в портфеле.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadGroupWriteRepo[Portfolio]
}

// NewHandler создает обработчик для актуализации портфелей с учетом нового списка торгуемых бумаг.
func NewHandler(pub domain.Publisher, repo domain.ReadGroupWriteRepo[Portfolio]) *Handler {
	return &Handler{pub: pub, repo: repo}
}

// Match выбирает событие обновления перечня бумаг.
func (h Handler) Match(event domain.Event) bool {
	_, ok := event.Data.(securities.Table)

	return ok && event.QID == securities.GroupID()
}

func (h Handler) String() string {
	return "securities -> accounts"
}

// Handle реагирует на событие об обновлении перечня бумаг и обновляет данные о лотах и торгуемых бумагах.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	secTable, ok := event.Data.(securities.Table)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	event.QID = ID(_Group)

	aggs, err := h.repo.GetGroup(ctx, portfolio.Subdomain, _Group)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	aggs, err = h.init(ctx, event, aggs)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	for _, agg := range aggs {
		event.QID = agg.QID()

		errs := agg.Entity.UpdateSec(secTable, event.Timestamp.After(agg.Timestamp))
		if len(errs) != 0 {
			h.pubErr(event, errs)

			return
		}

		agg.Timestamp = event.Timestamp

		if err := h.repo.Save(ctx, agg); err != nil {
			event.Data = err
			h.pub.Publish(event)

			return
		}
	}
}

func (h Handler) init(
	ctx context.Context,
	event domain.Event,
	aggs []domain.Aggregate[Portfolio],
) ([]domain.Aggregate[Portfolio], error) {
	if len(aggs) > 0 {
		return aggs, nil
	}

	event.QID = ID(_NewAccount)

	agg, err := h.repo.Get(ctx, event.QID)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return nil, err
	}

	return append(aggs, agg), nil
}

func (h Handler) pubErr(event domain.Event, errs []error) {
	for _, err := range errs {
		event.Data = err
		h.pub.Publish(event)
	}
}
