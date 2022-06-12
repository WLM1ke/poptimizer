package div

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

// CheckRawHandler обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
type CheckRawHandler struct {
	pub  domain.Publisher
	repo domain.ReadRepo[RawTable]
}

// NewCheckRawHandler новый обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
func NewCheckRawHandler(
	pub domain.Publisher,
	repo domain.ReadRepo[RawTable],
) *CheckRawHandler {
	return &CheckRawHandler{
		repo: repo,
		pub:  pub,
	}
}

// Match выбирает события изменения статуса дивидендов по отдельным тикерам.
func (h CheckRawHandler) Match(event domain.Event) bool {
	_, ok := event.Data.(Status)

	return ok && event.QualifiedID == StatusID(event.ID)
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

	qid := domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: RawGroup,
		ID:    event.ID,
	}

	event.QualifiedID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	n := sort.Search(
		len(table.Entity),
		func(i int) bool { return !table.Entity[i].Date.Before(status.Date) },
	)

	if (n == len(table.Entity)) || !status.Date.Equal(table.Entity[n].Date) {
		event.Data = fmt.Errorf(
			"%s missed dividend at %s",
			event.ID,
			status.Date.Format(_eventDateFormat),
		)
		h.pub.Publish(event)
	}
}
