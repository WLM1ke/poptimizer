package dates

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[domain.Date], rows []domain.Date) error {
	if len(rows) != 1 {
		return fmt.Errorf("%w: wrong rows count %d", template.ErrNewRowsValidation, len(rows))
	}

	return nil
}
