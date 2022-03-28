package template

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

// Selector - формирует слайс ID таблиц для обновления.
type Selector interface {
	Select(ctx context.Context, event domain.Event) ([]domain.ID, error)
}
