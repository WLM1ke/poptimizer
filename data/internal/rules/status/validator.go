package status

import (
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[DivStatus], rows []DivStatus) error {
	prev := rows[0].Ticker
	for _, row := range rows[1:] {
		if prev < row.Ticker {
			prev = row.Ticker
			continue
		}

		return fmt.Errorf("%w: not increasing tickers %+v", template.ErrNewRowsValidation, prev)
	}

	return nil
}
