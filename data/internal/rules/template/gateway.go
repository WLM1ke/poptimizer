package template

import (
	"context"
	"errors"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"time"
)

var ErrRuleGateway = errors.New("rule gateway error")

type Gateway[R any] interface {
	Get(ctx context.Context, table domain.Table[R], date time.Time) ([]R, error)
}
