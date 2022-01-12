package usd

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
)

const _group = "usd"

var ID = domain.NewId(_group, _group)

type selector struct {
}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if domain.CompareID(event, dates.ID) {
		return []domain.ID{ID}, nil
	}

	return nil, nil
}
