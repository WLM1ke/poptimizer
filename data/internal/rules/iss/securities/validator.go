package securities

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(_ domain.Table[domain.Security], rows []domain.Security) error {
	prev := rows[0].Ticker
	for _, row := range rows[1:] {
		if prev < row.Ticker {
			prev = row.Ticker

			continue
		}

		return fmt.Errorf("%w: not increasing tickers %+v", domain.ErrRule, prev)
	}

	return nil
}
