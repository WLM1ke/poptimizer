package dividends

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID().Group() == domain.QuotesGroup {
			ids = append(ids, domain.NewDividendsID(string(selected.Name())))
		}
	}

	return ids, err
}
