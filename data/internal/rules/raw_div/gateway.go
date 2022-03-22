package raw_div

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/status"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"sort"
	"time"
)

const _format = `2006-01-02`

type gateway struct {
	statusRepo repo.Read[domain.DivStatus]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.RawDiv], _ time.Time) ([]domain.RawDiv, error) {
	divStatus, err := s.statusRepo.Get(ctx, status.ID)
	if err != nil {
		return nil, err
	}

	statusRows := divStatus.Rows()
	ticker := string(table.Name())

	n := sort.Search(
		len(statusRows),
		func(i int) bool { return statusRows[i].Ticker >= ticker },
	)

	rawRows := table.Rows()
	for _, row := range statusRows[n:] {
		if row.Ticker != ticker {
			break
		}

		n := sort.Search(
			len(rawRows),
			func(i int) bool { return !rawRows[i].Date.Before(row.Date) },
		)

		if (n == len(rawRows)) || !row.Date.Equal(rawRows[n].Date) {
			return nil, fmt.Errorf(
				"%w: %s missed dividend at %s",
				template.ErrRuleGateway,
				ticker,
				row.Date.Format(_format),
			)
		}
	}

	return nil, nil
}
