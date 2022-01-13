package usd

import (
	"context"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"time"
)

const (
	_format = `2006-01-02`
	_ticker = `USD000UTSTOM`
)

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(ctx context.Context, table domain.Table[gomoex.Candle], date time.Time) ([]gomoex.Candle, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Begin.Format(_format)
	}

	end := date.Format(_format)

	rows, err := g.iss.MarketCandles(
		ctx,
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_ticker,
		start,
		end,
		gomoex.IntervalDay,
	)

	if err != nil {
		return nil, err
	}

	return rows, nil
}
