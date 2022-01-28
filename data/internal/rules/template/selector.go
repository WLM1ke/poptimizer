package template

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type Selector interface {
	Select(ctx context.Context, event domain.Event) ([]domain.ID, error)
}

type SelectOnTableUpdate struct {
	on     domain.ID
	update domain.ID
}

func NewSelectOnTableUpdate(on domain.ID, update domain.ID) SelectOnTableUpdate {
	return SelectOnTableUpdate{on: on, update: update}
}

func (s SelectOnTableUpdate) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID == s.on {
			ids = append(ids, s.update)
		}
	}

	return ids, err
}
