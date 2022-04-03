package dividends

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/quotes"
)

const Group = "dividends"

type selector struct{}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID().Group() == quotes.Group {
			ids = append(ids, domain.NewID(Group, string(selected.Name())))
		}
	}

	return ids, err
}
