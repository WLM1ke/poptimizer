package port

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

// SelectedGroup группа информации о выбранных для анализа тикерах.
const SelectedGroup = "selected"

// Selected выбранные для анализа тикеры.
type Selected map[string]bool

// SelectedHandler обработчик событий, отвечающий за обновление информации о выбранных для анализа тикерах.
type SelectedHandler struct {
	domain.Filter
	repo domain.ReadWriteRepo[Selected]
}

// NewSelectedHandler создает обработчик событий, отвечающий за обновление информации о выбранных тикерах.
func NewSelectedHandler(
	repo domain.ReadWriteRepo[Selected],
) *SelectedHandler {
	return &SelectedHandler{
		Filter: domain.Filter{
			Sub:   data.Subdomain,
			Group: data.SecuritiesGroup,
			ID:    data.SecuritiesGroup,
		},
		repo: repo,
	}
}

// Handle реагирует на событие об торгуемых бумагах, и обновляет список выбранных.
func (h SelectedHandler) Handle(ctx context.Context, event domain.Event) error {
	qid := domain.QualifiedID{
		Sub:   Subdomain,
		Group: SelectedGroup,
		ID:    SelectedGroup,
	}

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		return err
	}

	sec, ok := event.Data.(data.Rows[data.Security])
	if !ok {
		return fmt.Errorf("can't parse data in %s", event)
	}

	table.Timestamp = event.Timestamp
	table.Data = h.convert(sec, table.Data)

	if err := h.repo.Save(ctx, table); err != nil {
		return err
	}

	return nil
}

func (h SelectedHandler) convert(sec data.Rows[data.Security], old Selected) Selected {
	selected := make(Selected, len(sec))

	for _, row := range sec {
		selected[row.Ticker] = old[row.Ticker]
	}

	return selected
}
