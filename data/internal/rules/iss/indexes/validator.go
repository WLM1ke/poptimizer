package indexes

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

func validator(table domain.Table[domain.Index], rows []domain.Index) error {
	prev := rows[0].Date
	for _, row := range rows[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v and %+v", prev, row.Date)
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
