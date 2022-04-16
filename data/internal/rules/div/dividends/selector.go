package dividends

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID().Group() == domain.QuotesGroup {
			return []domain.ID{domain.NewDividendsID(string(selected.Name()))}, nil
		}
	}

	return nil, nil
}
