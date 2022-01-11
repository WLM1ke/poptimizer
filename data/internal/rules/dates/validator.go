package dates

import (
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[gomoex.Date], rows []gomoex.Date) error {
	if len(rows) != 1 {
		return fmt.Errorf("%w: wrong rows count %d", template.ErrNewRowsValidation, len(rows))
	}

	return nil
}
