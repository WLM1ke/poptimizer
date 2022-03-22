package securities

import (
	"context"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"sort"
	"time"
)

const _engine = gomoex.EngineStock

var marketsBoards = []struct {
	market string
	board  string
}{
	{gomoex.MarketShares, gomoex.BoardTQBR},
	{gomoex.MarketShares, gomoex.BoardTQTF},
	{gomoex.MarketForeignShares, gomoex.BoardFQBR},
}

type gateway struct {
	iss *gomoex.ISSClient
}

func (g gateway) Get(
	ctx context.Context,
	_ domain.Table[domain.Security],
	_ time.Time,
) (allRows []gomoex.Security, err error) {
	for _, mb := range marketsBoards {
		rows, err := g.iss.BoardSecurities(ctx, _engine, mb.market, mb.board)
		if err != nil {
			return nil, err
		}
		allRows = append(allRows, rows...)
	}

	sort.Slice(allRows, func(i, j int) bool { return allRows[i].Ticker < allRows[j].Ticker })

	return allRows, nil
}
