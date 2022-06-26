package market

import (
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"golang.org/x/exp/slices"
)

const (
	_Group      = `market_data`
	_month      = 21
	_year       = 12 * _month
	_minHistory = 2 * (_month + _year)
)

// ID рыночных данных для заданного тикера.
func ID(ticker string) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _Group,
		ID:    ticker,
	}
}

// Data представляет информацию об актуальной рыночной цене и обороте.
type Data struct {
	Price    float64
	Turnover float64
}

// Update обновляет рыночные данные.
//
// Берется последняя цена закрытия и минимальная медиана оборота за месяц, год и два года.
func (d *Data) Update(quotes quote.Table) {
	d.Price = quotes[len(quotes)-1].Close
	d.Turnover = minMedTurnover(quotes)
}

func minMedTurnover(quotes quote.Table) float64 {
	turnover := make([]float64, _minHistory)

	lenQuotes := len(quotes)

	lenMin := _minHistory
	if lenQuotes < lenMin {
		lenMin = lenQuotes
	}

	for i := 0; i < lenMin; i++ {
		turnover[_minHistory-1-i] = quotes[lenQuotes-1-i].Turnover
	}

	med := median(turnover, _month)

	if medYear := median(turnover, _year); medYear < med {
		med = medYear
	}

	if medFull := median(turnover, _minHistory); medFull < med {
		med = medFull
	}

	return med
}

func median(turnover []float64, lookBack int) float64 {
	turnover = turnover[len(turnover)-lookBack:]
	slices.Sort(turnover)

	if lookBack%2 == 0 {
		return (turnover[lookBack/2-1] + turnover[lookBack/2]) / 2 //nolint:gomnd
	}

	return turnover[lookBack/2]
}
