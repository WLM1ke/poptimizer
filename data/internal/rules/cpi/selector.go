package cpi

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/dates"
)

const _group = "cpi"

var ID = domain.NewID(_group, _group)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == dates.ID {
			ids = append(ids, ID)
		}
	}

	return ids, err
}
