package quotes

import (
	"context"
	"fmt"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
)

type selector struct {
	securities repo.Read[gomoex.Security]
}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == domain.NewSecuritiesID() {
			sec, err := s.securities.Get(ctx, domain.NewSecuritiesID())
			if err != nil {
				return ids, fmt.Errorf(
					"can't load from repo -> %w",
					err,
				)
			}

			for _, s := range sec.Rows() {
				ids = append(ids, domain.NewQuotesID(s.Ticker))
			}
		}
	}

	return ids, err
}
