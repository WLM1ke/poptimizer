package dividends

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

func (s selector) Select(ctx context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewSecuritiesID() {
			return s.ids(ctx)
		}
	}

	return nil, nil
}

func (s selector) ids(ctx context.Context) ([]domain.ID, error) {
	sec, err := s.securities.Get(ctx, domain.NewSecuritiesID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load from repo -> %w",
			err,
		)
	}

	ids := make([]domain.ID, 0, len(sec.Rows()))

	for _, s := range sec.Rows() {
		ids = append(ids, domain.NewDividendsID(s.Ticker))
	}

	return ids, nil
}
