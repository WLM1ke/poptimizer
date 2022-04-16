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

func (s selector) Select(ctx context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewDivStatusID() {
			return s.ids(ctx)
		}
	}

	return nil, nil
}

func (s selector) ids(ctx context.Context) ([]domain.ID, error) {
	sec, err := s.repo.Get(ctx, domain.NewDivStatusID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load dividends status from repo -> %w",
			err,
		)
	}

	var ids []domain.ID

	for _, s := range sec.Rows() {
		ids = append(ids, domain.NewRawDivID(s.Ticker))
	}

	return ids, nil
}
