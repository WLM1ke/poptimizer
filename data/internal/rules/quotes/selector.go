package quotes

import (
	"context"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
)

const Group = "quotes"

type selector struct {
	securities repo.Read[gomoex.Security]
}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == securities.ID {
			sec, err := s.securities.Get(ctx, securities.ID)
			if err != nil {
				return ids, err
			}

			for _, s := range sec.Rows() {
				ids = append(ids, domain.NewID(Group, s.Ticker))
			}
		}
	}

	return ids, err
}
