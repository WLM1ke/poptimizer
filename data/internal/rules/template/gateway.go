package template

import (
	"context"
	"errors"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

// ErrRuleGateway - базовая ошибка при загрузке необходимых для обновления данных.
var ErrRuleGateway = errors.New("rule gateway error")

// Gateway загружает необходимые данные и формирует слайс новых строк.
type Gateway[R domain.Row] interface {
	Get(ctx context.Context, table domain.Table[R]) ([]R, error)
}
