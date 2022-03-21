package dividends

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"
	"golang.org/x/exp/slices"
	"sort"
	"time"
)

type Currency string

const (
	USD     = `USD`
	RUR     = `RUR`
	_rawDiv = `raw_div`
)

type RawDiv struct {
	Date     time.Time
	Value    float64
	Currency Currency
}

type Dividend struct {
	Date  time.Time
	Value float64
}

type gateway struct {
	rawRepo repo.Read[RawDiv]
	usdRepo repo.Read[gomoex.Candle]
}

func (s gateway) Get(ctx context.Context, table domain.Table[Dividend], _ time.Time) ([]Dividend, error) {
	raw, err := s.rawRepo.Get(ctx, domain.NewID(_rawDiv, string(table.Name())))
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

func (s gateway) prepareDiv(raw []RawDiv, rates []gomoex.Candle) (dividends []Dividend, err error) {
	var date time.Time

	for _, div := range raw {
		if !div.Date.Equal(date) {
			date = div.Date
			dividends = append(dividends, Dividend{Date: date})
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
