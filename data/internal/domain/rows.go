package domain

import (
	"time"

	"github.com/WLM1ke/gomoex"
)

type (
	// Date - торговые даты.
	Date = gomoex.Date
	// Index - котировки индекса.
	Index = gomoex.Quote
	// USD - свечки курса доллара.
	USD = gomoex.Candle
	// Security - информация об акции.
	Security = gomoex.Security
	// Quote - свечки акций и ETF.
	Quote = gomoex.Candle
)

// CPI - месячные данные об инфляции.
type CPI struct {
	Date  time.Time
	Value float64
}

// Ticker - для которого нужно отслеживать статус дивидендов.
type Ticker string

// DivStatus - информация об ожидаемых датах выплаты дивидендов.
type DivStatus struct {
	Ticker string
	Date   time.Time
}

// RawDiv - введенные вручную данные о дивидендах с указанием валюты выплаты.
type RawDiv struct {
	Date     time.Time
	Value    float64
	Currency string
}

// Dividend - данные о дивидендах переведенные в рубли и объединенные при нескольких выплатах в одну дату.
type Dividend struct {
	Date  time.Time
	Value float64
}

// Row - строки данных в таблицах.
type Row interface {
	Date | CPI | Index | USD | Security | Ticker | DivStatus | RawDiv | Dividend
}
