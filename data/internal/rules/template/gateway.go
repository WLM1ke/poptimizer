package template

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"time"
)

type Gateway[R any] func(ctx context.Context, table domain.Table[R], date time.Time) ([]R, error)
