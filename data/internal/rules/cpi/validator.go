package cpi

import (
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(table domain.Table[domain.CPI], rows []domain.CPI) error {
	if table.IsEmpty() {
		return nil
	}

	for n, row := range table.Rows() {
		if row != rows[n] {
			return fmt.Errorf(
				"%w: old row %+v not match new %+v",
				template.ErrNewRowsValidation,
				row,
				rows[n],
			)
		}
	}

	return nil
}
