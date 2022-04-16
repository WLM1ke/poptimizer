package dates

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewDayEndedID() {
			return []domain.ID{domain.NewTradingDateID()}, nil
		}
	}

	return nil, nil
}
