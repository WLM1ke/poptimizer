package dates

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/end"
)

const _group = "dates"

var ID = domain.NewId(_group, _group)

type selector struct {
}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if domain.CompareID(event, end.ID) {
		return []domain.ID{ID}, nil
	}

	return nil, nil
}
