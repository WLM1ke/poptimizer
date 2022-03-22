package template

import (
	"errors"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

var ErrNewRowsValidation = errors.New("new rows validation error")

type Validator[R domain.Row] func(table domain.Table[R], rows []R) error
