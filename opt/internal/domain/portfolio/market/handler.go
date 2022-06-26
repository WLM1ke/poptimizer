package market

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
)

// Handler обработчик событий, отвечающий за обновление рыночных данных, необходимых для портфеля.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadWriteRepo[Data]
}

// NewHandler создает обработчик события для обновления рыночных данных, необходимых для портфеля.
func NewHandler(pub domain.Publisher, repo domain.ReadWriteRepo[Data]) *Handler {
	return &Handler{pub: pub, repo: repo}
}

// Match выбирает события обновления котировок.
func (h Handler) Match(event domain.Event) bool {
	_, ok := event.Data.(quote.Table)

	return ok && event.QID == quote.ID(event.ID)
}

func (h Handler) String() string {
	return "quotes -> market data"
}

// Handle реагирует на события об обновлении котировок и обновляет рыночные данные.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	quotes, ok := event.Data.(quote.Table)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	event.QID = ID(event.ID)

	agg, err := h.repo.Get(ctx, event.QID)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	agg.Timestamp = event.Timestamp
	agg.Entity.Update(quotes)

	if err := h.repo.Save(ctx, agg); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	event.Data = agg.Entity

	h.pub.Publish(event)
}
