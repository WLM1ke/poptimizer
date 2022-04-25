package usd

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewTradingDateID() {
			return []domain.ID{domain.NewUsdID()}, nil
		}
	}

	return nil, nil
}