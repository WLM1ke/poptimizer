package status

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/dates"
)

const _group = "status"

func NewID() domain.ID {
	return domain.NewID(_group, _group)
}

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == dates.ID {
			ids = append(ids, NewID())
		}
	}

	return ids, err
}
