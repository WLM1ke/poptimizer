package dividends

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"golang.org/x/exp/slices"
)

type gateway struct {
	rawRepo repo.Read[domain.RawDiv]
	usdRepo repo.Read[domain.USD]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.Dividend]) ([]domain.Dividend, error) {
	rawDiv, err := s.rawRepo.Get(ctx, domain.NewRawDivID(string(table.Name())))
	if err != nil {
		return nil, fmt.Errorf(
			"can't load from repo -> %w",
			err,
		)
	}

	if rawDiv.IsEmpty() {
		return nil, nil
	}

	rate, err := s.usdRepo.Get(ctx, domain.NewUsdID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load from repo -> %w",
			err,
		)
	}

	div, err := s.prepareDiv(rawDiv.Rows(), rate.Rows())
	if err != nil {
		return nil, err
	}

	if slices.Equal(div, table.Rows()) {
		return nil, nil
	}

	return div, nil
}

func (s gateway) prepareDiv(rawDivs []domain.RawDiv, rates []gomoex.Candle) (dividends []domain.Dividend, err error) {
	var date time.Time

	for _, row := range rawDivs {
		if !row.Date.Equal(date) {
			date = row.Date

			dividends = append(dividends, domain.Dividend{Date: date})
		}

		switch row.Currency {
		case domain.RURCurrency:
			dividends[len(dividends)-1].Value += row.Value
		case domain.USDCurrency:
			n := sort.Search(
				len(rates),
				func(i int) bool { return rates[i].Begin.After(date) },
			)
			dividends[len(dividends)-1].Value += row.Value * rates[n-1].Close
		default:
			return nil, fmt.Errorf(
				"unknown currency %+v",
				row.Currency,
			)
		}
	}

	return dividends, nil
}
