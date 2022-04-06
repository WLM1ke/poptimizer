package dividends

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(_ domain.Table[domain.Dividend], rows []domain.Dividend) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("%w: not increasing dates %+v and %+v", domain.ErrRule, prev, row.Date)
	}

	return nil
}
