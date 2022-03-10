package quotes

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
)

const _group = "quotes"

func (s *selectorWithGateway) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == securities.ID {
			s.lock.Lock()
			defer s.lock.Unlock()

			sec, err := s.repo.Get(ctx, securities.ID)
			if err != nil {
				return ids, err
			}

			s.securities = sec.Rows()

			for _, s := range sec.Rows() {
				ids = append(ids, domain.NewID(_group, s.Ticker))
			}
		}
	}

	return ids, err
}
