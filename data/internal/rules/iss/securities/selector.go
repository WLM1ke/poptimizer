package securities

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/usd"
)

const _group = "securities"

var ID = domain.NewID(_group, _group)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == usd.ID {
			ids = append(ids, ID)
		}
	}

	return ids, err
}
