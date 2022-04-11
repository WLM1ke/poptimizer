package securities

import (
	"context"
	"fmt"
	"sort"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(
	ctx context.Context,
	_ domain.Table[domain.Security],
) (allRows []gomoex.Security, err error) {
	marketsBoards := []struct {
		market string
		board  string
	}{
		{gomoex.MarketShares, gomoex.BoardTQBR},
		{gomoex.MarketShares, gomoex.BoardTQTF},
		{gomoex.MarketForeignShares, gomoex.BoardFQBR},
	}

	for _, mb := range marketsBoards {
		rows, err := g.iss.BoardSecurities(ctx, gomoex.EngineStock, mb.market, mb.board)
		if err != nil {
			return nil, fmt.Errorf(
				"can't download securities data -> %w",
				err,
			)
		}

		allRows = append(allRows, rows...)
	}

	sort.Slice(allRows, func(i, j int) bool { return allRows[i].Ticker < allRows[j].Ticker })

	return allRows, nil
}
