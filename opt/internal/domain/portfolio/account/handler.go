package account

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

// Handler обработчик событий, отвечающий за обновление перечня выбранных бумаг на счетах.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadGroupWriteRepo[Account]
}

// NewHandler создает обработчик для актуализации брокерских счетов с учетом нового списка торгуемых бумаг.
func NewHandler(pub domain.Publisher, repo domain.ReadGroupWriteRepo[Account]) *Handler {
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

	event.QID = GroupID()

	aggs, err := h.repo.GetGroup(ctx, portfolio.Subdomain, _Group)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if len(aggs) == 0 {
		event.QID = ID(_NewAccount)

		agg, err := h.repo.Get(ctx, event.QID)
		if err != nil {
			event.Data = err
			h.pub.Publish(event)

			return
		}

		aggs = append(aggs, agg)
	}

	for _, agg := range aggs {
		event.QID = agg.QID()

		agg.Timestamp = event.Timestamp

		errs := agg.Entity.Update(secTable)
		if len(errs) != 0 {
			h.pubErr(event, errs)

			return
		}

		if err := h.repo.Save(ctx, agg); err != nil {
			event.Data = err
			h.pub.Publish(event)

			return
		}
	}

	h.pubAllAccounts(aggs)
}

func (h Handler) pubErr(event domain.Event, errs []error) {
	for _, err := range errs {
		event.Data = err
		h.pub.Publish(event)
	}
}

func (h Handler) pubAllAccounts(aggs []domain.Aggregate[Account]) {
	allAccounts := aggs[0].Entity

	for _, agg := range aggs[1:] {
		allAccounts = allAccounts.Sum(agg.Entity)
	}

	h.pub.Publish(domain.Event{
		QID:       GroupID(),
		Timestamp: aggs[0].Timestamp,
		Data:      allAccounts,
	})
}
