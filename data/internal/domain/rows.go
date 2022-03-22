package domain

import (
	"github.com/WLM1ke/gomoex"
	"time"
)

type (
	Date     = gomoex.Date
	Index    = gomoex.Quote
	USD      = gomoex.Candle
	Security = gomoex.Security
	Quote    = gomoex.Candle
)

type CPI struct {
	Date  time.Time
	Value float64
}

type DivStatus struct {
	Ticker string
	Date   time.Time
}

type RawDiv struct {
	Date     time.Time
	Value    float64
	Currency string
}

type Dividend struct {
	Date  time.Time
	Value float64
}

type Row interface {
	Date | CPI | Index | USD | Security | DivStatus | RawDiv | Dividend
}
