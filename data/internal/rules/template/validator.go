package template

import (
	"errors"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

// ErrNewRowsValidation базовая ошибка валидации.
var ErrNewRowsValidation = errors.New("new rows validation error")

// Validator проверят корректность новых данных и стыковки со старыми данными.
type Validator[R domain.Row] func(table domain.Table[R], rows []R) error
