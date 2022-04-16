package nasdaq

import (
	"context"
	"fmt"
	"strings"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
)

const _foreignSuffix = `-RM`

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
				if isForeignShare(s.Ticker) {
					ids = append(ids, domain.NewNASDAQDivID(s.Ticker))
				}
			}
		}
	}

	return ids, err
}

func isForeignShare(ticker string) bool {
	return strings.HasSuffix(ticker, _foreignSuffix)
}
