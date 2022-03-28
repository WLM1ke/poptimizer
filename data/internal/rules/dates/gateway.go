package dates

import (
	"context"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(ctx context.Context, table domain.Table[domain.Date], _ time.Time) ([]domain.Date, error) {
	rows, err := g.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)

	switch {
	case err != nil:
		return nil, err
	case table.IsEmpty():
		return rows, nil
	case table.LastRow().Till.Before(rows[0].Till):
		return rows, nil
	default:
		return nil, nil
	}
}
