package usd

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(table domain.Table[domain.USD], rows []domain.USD) error {
	prev := rows[0].Begin
	for _, row := range rows[1:] {
		if prev.Before(row.Begin) {
			prev = row.Begin

			continue
		}

		return fmt.Errorf("%w: not increasing dates %+v", domain.ErrRule, prev)
	}

	if table.IsEmpty() {
		return nil
	}

	if table.LastRow() != rows[0] {
		return fmt.Errorf(
			"%w: old rows %+v not match new %+v",
			domain.ErrRule,
			table.LastRow(),
			rows[0])
	}

	return nil
}
