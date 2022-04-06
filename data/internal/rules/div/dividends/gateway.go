package dividends

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/div/raw"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/usd"
	"golang.org/x/exp/slices"
)

type gateway struct {
	rawRepo repo.Read[domain.RawDiv]
	usdRepo repo.Read[domain.USD]
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.Dividend]) ([]domain.Dividend, error) {
	rawDiv, err := s.rawRepo.Get(ctx, domain.NewID(raw.Group, string(table.Name())))
	if err != nil {
		return nil, fmt.Errorf(
			"%w: can't load from repo -> %s",
			domain.ErrRule,
			err,
		)
	}

	if rawDiv.IsEmpty() {
		return nil, nil
	}

	rate, err := s.usdRepo.Get(ctx, usd.ID)
	if err != nil {
		return nil, fmt.Errorf(
			"%w: can't load from repo -> %s",
			domain.ErrRule,
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
		case raw.RUR:
			dividends[len(dividends)-1].Value += row.Value
		case raw.USD:
			n := sort.Search(
				len(rates),
				func(i int) bool { return rates[i].Begin.After(date) },
			)
			dividends[len(dividends)-1].Value += row.Value * rates[n-1].Close
		default:
			return nil, fmt.Errorf(
				"%w: unknown currency %+v",
				domain.ErrRule,
				row.Currency,
			)
		}
	}

	return dividends, nil
}
