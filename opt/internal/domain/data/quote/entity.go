package quote

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const _QuotesGroup = "quotes"

// ID котировок заданного тикера.
func ID(ticker string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _QuotesGroup,
		ID:    ticker,
	}
}

// Quote свечка.
type Quote struct {
	Date     time.Time
	Open     float64
	Close    float64
	High     float64
	Low      float64
	Turnover float64
}

// Table - таблица с котировками для определенной бумаги.
type Table = data.Table[Quote]
