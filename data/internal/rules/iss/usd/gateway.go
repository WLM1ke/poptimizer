package usd

import (
	"context"
	"fmt"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

const (
	_format = `2006-01-02`
	_ticker = `USD000UTSTOM`
)

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(ctx context.Context, table domain.Table[domain.USD]) ([]domain.USD, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Begin.Format(_format)
	}

	end := domain.LastTradingDate().Format(_format)

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
		return nil, fmt.Errorf(
			"can't download usd data -> %w",
			err,
		)
	}

	return rows, nil
}
