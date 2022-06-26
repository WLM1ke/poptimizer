package raw

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// CheckRawHandler обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
type CheckRawHandler struct {
	pub  domain.Publisher
	repo domain.ReadRepo[Table]
}

// NewCheckRawHandler новый обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
func NewCheckRawHandler(
	pub domain.Publisher,
	repo domain.ReadRepo[Table],
) *CheckRawHandler {
	return &CheckRawHandler{
		repo: repo,
		pub:  pub,
	}
}

// Match выбирает события изменения статуса дивидендов по отдельным тикерам.
func (h CheckRawHandler) Match(event domain.Event) bool {
	_, ok := event.Data.(Status)

	return ok && event.QID == StatusID(event.ID)
}

func (h CheckRawHandler) String() string {
	return "dividend status -> check raw dividends"
}

// Handle реагирует на событие об обновлении статуса дивидендов и проверяет пользовательские дивиденды.
func (h CheckRawHandler) Handle(ctx context.Context, event domain.Event) {
	status, ok := event.Data.(Status)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := ID(event.ID)

	event.QID = qid

	agg, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if !agg.Entity.ExistsDate(status.Date) {
		event.Data = fmt.Errorf(
			"missed dividend at %s",
			status.Date.Format(_eventDateFormat),
		)
		h.pub.Publish(event)
	}
}
