package reestry

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(_ domain.Table[domain.CurrencyDiv], rows []domain.CurrencyDiv) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if !prev.After(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v and %+v", prev, row.Date)
	}

	return nil
}
