package dividends

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"
	"golang.org/x/exp/slices"
)

const (
	USD = `USD`
	RUR = `RUR`
)

type gateway struct {
	rawRepo repo.Read[domain.RawDiv]
	usdRepo repo.Read[domain.USD]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.Dividend]) ([]domain.Dividend, error) {
	raw, err := s.rawRepo.Get(ctx, domain.NewID(raw_div.Group, string(table.Name())))
	if err != nil {
		return nil, err
	}

	if raw.IsEmpty() {
		return nil, nil
	}

	rate, err := s.usdRepo.Get(ctx, usd.ID)
	if err != nil {
		return nil, err
	}

	div, err := s.prepareDiv(raw.Rows(), rate.Rows())
	if err != nil {
		return nil, err
	}

	if slices.Equal(div, table.Rows()) {
		return nil, nil
	}

	return div, nil
}

func (s gateway) prepareDiv(raw []domain.RawDiv, rates []gomoex.Candle) (dividends []domain.Dividend, err error) {
	var date time.Time

	for _, div := range raw {
		if !div.Date.Equal(date) {
			date = div.Date
			dividends = append(dividends, domain.Dividend{Date: date})
		}

		switch div.Currency {
		case RUR:
			dividends[len(dividends)-1].Value += div.Value
		case USD:
			n := sort.Search(
				len(rates),
				func(i int) bool { return rates[i].Begin.After(date) },
			)
			dividends[len(dividends)-1].Value += div.Value * rates[n-1].Close
		default:
			return nil, fmt.Errorf(
				"%w: unknown currency %+v",
				template.ErrRuleGateway,
				div.Currency,
			)
		}
	}

	return dividends, nil
}
