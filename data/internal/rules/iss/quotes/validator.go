package quotes

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(table domain.Table[domain.Quote], rows []domain.Quote) error {
	prev := rows[0].Begin
	for _, row := range rows[1:] {
		if prev.Before(row.Begin) {
			prev = row.Begin

			continue
		}

		return fmt.Errorf("not increasing dates %+v and %+v", prev, row.Begin)
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
