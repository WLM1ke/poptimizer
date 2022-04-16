package cpi

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewTradingDateID() {
			return []domain.ID{domain.NewCpiID()}, nil
		}
	}

	return nil, nil
}
