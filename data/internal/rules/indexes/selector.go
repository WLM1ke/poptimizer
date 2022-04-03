package indexes

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
)

const _group = "indexes"

var indexes = []string{
	`MCFTRR`,
	`MEOGTRR`,
	`IMOEX`,
	`RVI`,
}

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == dates.ID {
			for _, index := range indexes {
				ids = append(ids, domain.NewID(_group, index))
			}
		}
	}

	return ids, err
}
