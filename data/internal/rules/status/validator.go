package status

import (
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[domain.DivStatus], rows []domain.DivStatus) error {
	prev := rows[0]
	for _, row := range rows[1:] {
		if prev.Ticker > row.Ticker {
			return fmt.Errorf("%w: not increasing tickers %+v and %+v", template.ErrNewRowsValidation, prev, row)
		}

		if (prev.Ticker == row.Ticker) && prev.Date.After(row.Date) {
			return fmt.Errorf("%w: not increasing dates %+v and %+v", template.ErrNewRowsValidation, prev, row)
		}

		prev = row
	}

	return nil
}
