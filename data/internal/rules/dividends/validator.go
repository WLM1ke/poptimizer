package dividends

import (
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[Dividend], rows []Dividend) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date
			continue
		}

		return fmt.Errorf("%w: not increasing dates %+v and %+v", template.ErrNewRowsValidation, prev, row.Date)
	}

	return nil
}
