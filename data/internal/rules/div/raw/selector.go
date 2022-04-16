package raw

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
)

type selector struct {
	repo repo.Read[domain.DivStatus]
}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == domain.NewDivStatusID() {
			sec, err := s.repo.Get(ctx, domain.NewDivStatusID())
			if err != nil {
				return ids, fmt.Errorf(
					"can't load dividends status from repo -> %w",
					err,
				)
			}

			for _, s := range sec.Rows() {
				ids = append(ids, domain.NewRawDivID(s.Ticker))
			}
		}
	}

	return ids, err
}
