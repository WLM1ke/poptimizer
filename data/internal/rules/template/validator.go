package template

import "github.com/WLM1ke/poptimizer/data/internal/domain"

type Validator[R any] func(table domain.Table[R], rows []R) error