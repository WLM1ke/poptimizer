package securities

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == domain.NewUsdID() {
			ids = append(ids, domain.NewSecuritiesID())
		}
	}

	return ids, err
}
