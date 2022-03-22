package raw_div

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/status"
)

const Group = "raw_div"

type selector struct {
	repo repo.Read[domain.DivStatus]
}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == status.ID {

			sec, err := s.repo.Get(ctx, status.ID)
			if err != nil {
				return ids, err
			}

			for _, s := range sec.Rows() {
				ticker := s.Ticker
				_, ok := _portfolio[ticker]
				if ok {
					ids = append(ids, domain.NewID(Group, ticker))
				}
			}
		}
	}

	return ids, err
}
