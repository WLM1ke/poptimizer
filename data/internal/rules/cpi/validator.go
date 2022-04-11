package cpi

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(table domain.Table[domain.CPI], rows []domain.CPI) error {
	if table.IsEmpty() {
		return nil
	}

	for num, row := range table.Rows() {
		if row != rows[num] {
			return fmt.Errorf(
				"old row %+v not match new %+v",
				row,
				rows[num],
			)
		}
	}

	return nil
}
