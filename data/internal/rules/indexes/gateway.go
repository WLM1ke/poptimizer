package indexes

import (
	"context"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"time"
)

const _format = `2006-01-02`

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(ctx context.Context, table domain.Table[gomoex.Quote], date time.Time) ([]gomoex.Quote, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Date.Format(_format)
	}

	end := date.Format(_format)

	rows, err := g.iss.MarketHistory(
		ctx,
		gomoex.EngineStock,
		gomoex.MarketIndex,
		string(table.Name()),
		start,
		end,
	)
	if err != nil {
		return nil, err
	}

	return rows, nil
}
