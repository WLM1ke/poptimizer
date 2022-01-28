package securities

import (
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
)

func validator(_ domain.Table[gomoex.Security], rows []gomoex.Security) error {
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
