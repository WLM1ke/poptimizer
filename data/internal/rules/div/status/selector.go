package status

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewSecuritiesID() {
			return []domain.ID{domain.NewDivStatusID()}, nil
		}
	}

	return nil, nil
}
