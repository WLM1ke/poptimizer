package template

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type Selector func(ctx context.Context, event domain.Event) ([]domain.ID, error)