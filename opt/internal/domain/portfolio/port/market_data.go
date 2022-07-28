package port

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"golang.org/x/exp/slices"
)

const (
	_month      = 21
	_year       = 12 * _month
	_minHistory = 2 * (_month + _year)
)

type markerData struct {
	Price    float64
	Turnover float64
}

// CalcMarkerData берет последнюю цену закрытия и минимальная медиана оборота за месяц, год и два года, если данные
// актуальные или ноль, если устаревшие.
func calcMarkerData(date time.Time, quotes quote.Table) markerData {
	var data markerData

	if len(quotes) > 0 {
		data.Price = quotes[len(quotes)-1].Close
	}

	if len(quotes) > 0 && quotes[len(quotes)-1].Date.Equal(date) {
		data.Turnover = minMedTurnover(quotes)
	}

	return data
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
