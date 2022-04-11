package quotes

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/securities"
)

const _format = `2006-01-02`

type gateway struct {
	iss     *gomoex.ISSClient
	secRepo repo.Read[gomoex.Security]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.Quote]) ([]domain.Quote, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Begin.Format(_format)
	}

	end := domain.LastTradingDate().Format(_format)
	ticker := string(table.Name())

	market, err := s.getMarket(ctx, ticker)
	if err != nil {
		return nil, err
	}

	rows, err := s.iss.MarketCandles(
		ctx,
		gomoex.EngineStock,
		market,
		ticker,
		start,
		end,
		gomoex.IntervalDay,
	)
	if err != nil {
		return nil, fmt.Errorf(
			"can't download quotes -> %w",
			err,
		)
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Begin.Before(rows[j].Begin) })

	return rows, nil
}

func (s gateway) getMarket(ctx context.Context, ticker string) (string, error) {
	table, err := s.secRepo.Get(ctx, securities.ID)
	if err != nil {
		return "", fmt.Errorf(
			"can't load from repo -> %w",
			err,
		)
	}

	sec := table.Rows()

	position := sort.Search(len(sec), func(i int) bool {
		return sec[i].Ticker >= ticker
	})

	switch sec[position].Board {
	case gomoex.BoardTQBR, gomoex.BoardTQTF:
		return gomoex.MarketShares, nil
	case gomoex.BoardFQBR:
		return gomoex.MarketForeignShares, nil
	}

	return "", fmt.Errorf(
		"wrong board %s for ticker %s",
		sec[position].Board,
		ticker,
	)
}
