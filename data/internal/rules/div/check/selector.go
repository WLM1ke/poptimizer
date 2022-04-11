package check

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/div/status"
)

const (
	// Group - группа вручную введенных дивидендов.
	Group = "raw_div"
	// USD - наименование валюты доллара.
	USD = `USD`
	// RUR - наименование валюты рубля.
	RUR = `RUR`
)

type selector struct {
	repo repo.Read[domain.DivStatus]
}

func (s selector) Select(ctx context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == status.NewID() {
			sec, err := s.repo.Get(ctx, status.NewID())
			if err != nil {
				return ids, fmt.Errorf(
					"can't load dividends status from repo -> %w",
					err,
				)
			}

			for _, s := range sec.Rows() {
				ticker := s.Ticker
				if _, ok := _portfolio[ticker]; ok {
					ids = append(ids, domain.NewID(Group, ticker))
				}
			}
		}
	}

	return ids, err
}
