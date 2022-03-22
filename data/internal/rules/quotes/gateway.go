package quotes

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"sort"
	"time"
)

const _format = `2006-01-02`

var boardToMarket = map[string]string{
	gomoex.BoardTQBR: gomoex.MarketShares,
	gomoex.BoardTQTF: gomoex.MarketShares,
	gomoex.BoardFQBR: gomoex.MarketForeignShares,
}

type gateway struct {
	iss     *gomoex.ISSClient
	secRepo repo.Read[gomoex.Security]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.Quote], date time.Time) ([]domain.Quote, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Begin.Format(_format)
	}

	end := date.Format(_format)
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
		return nil, err
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Begin.Before(rows[j].Begin) })

	return rows, nil
}

func (s gateway) getMarket(ctx context.Context, ticker string) (string, error) {
	table, err := s.secRepo.Get(ctx, securities.ID)
	if err != nil {
		return "", err
	}

	sec := table.Rows()

	n := sort.Search(len(sec), func(i int) bool {
		return sec[i].Ticker >= ticker
	})

	m, ok := boardToMarket[sec[n].Board]
	if ok {
		return m, nil
	}

	return "", fmt.Errorf(
		"%w: wrong board for ticker %s - %s",
		template.ErrRuleGateway,
		ticker,
		sec[n].Board,
	)
}
