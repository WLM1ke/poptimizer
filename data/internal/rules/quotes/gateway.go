package quotes

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"sort"
	"sync"
	"time"
)

const _format = `2006-01-02`

var boardToMarket = map[string]string{
	gomoex.BoardTQBR: gomoex.MarketShares,
	gomoex.BoardTQTF: gomoex.MarketShares,
	gomoex.BoardFQBR: gomoex.MarketForeignShares,
}

type selectorWithGateway struct {
	iss  *gomoex.ISSClient
	repo repo.Read[gomoex.Security]

	lock       sync.RWMutex
	securities []gomoex.Security
}

func (s *selectorWithGateway) Get(ctx context.Context, table domain.Table[gomoex.Candle], date time.Time) ([]gomoex.Candle, error) {
	start := ""
	if !table.IsEmpty() {
		start = table.LastRow().Begin.Format(_format)
	}

	end := date.Format(_format)
	ticker := string(table.Name())

	market, err := s.getMarket(ticker)
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

func (s *selectorWithGateway) getMarket(ticker string) (string, error) {
	s.lock.RLock()
	defer s.lock.RUnlock()

	n := sort.Search(len(s.securities), func(i int) bool {
		return s.securities[i].Ticker >= ticker
	})

	m, ok := boardToMarket[s.securities[n].Board]
	if ok {
		return m, nil
	}

	return "", fmt.Errorf(
		"%w: wrong board for ticker %s - %s",
		template.ErrRuleGateway,
		ticker,
		s.securities[n].Board,
	)
}
