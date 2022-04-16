package raw

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
)

const _format = `2006-01-02`

type gateway struct {
	statusRepo repo.Read[domain.DivStatus]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.CurrencyDiv]) ([]domain.CurrencyDiv, error) {
	divStatus, err := s.statusRepo.Get(ctx, domain.NewDivStatusID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load dividends status from repo -> %w",
			err,
		)
	}

	statusRows := divStatus.Rows()
	ticker := string(table.Name())

	position := sort.Search(
		len(statusRows),
		func(i int) bool { return statusRows[i].Ticker >= ticker },
	)

	rawRows := table.Rows()

	for _, row := range statusRows[position:] {
		if row.Ticker != ticker {
			break
		}

		n := sort.Search(
			len(rawRows),
			func(i int) bool { return !rawRows[i].Date.Before(row.Date) },
		)

		if (n == len(rawRows)) || !row.Date.Equal(rawRows[n].Date) {
			return nil, fmt.Errorf(
				"%s missed dividend at %s",
				ticker,
				row.Date.Format(_format),
			)
		}
	}

	return nil, nil
}
