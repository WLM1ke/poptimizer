package template

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

// Validator проверят корректность новых данных и стыковки со старыми данными.
type Validator[R domain.Row] func(table domain.Table[R], rows []R) error
