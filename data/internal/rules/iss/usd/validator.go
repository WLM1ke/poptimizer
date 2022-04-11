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

		return fmt.Errorf("not increasing dates %+v", prev)
	}

	if table.IsEmpty() {
		return nil
	}

	if table.LastRow() != rows[0] {
		return fmt.Errorf(
			"old rows %+v not match new %+v",
			table.LastRow(),
			rows[0])
	}

	return nil
}
