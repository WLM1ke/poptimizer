package template

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

// Gateway загружает необходимые данные и формирует слайс новых строк.
type Gateway[R domain.Row] interface {
	Get(ctx context.Context, table domain.Table[R]) ([]R, error)
}
