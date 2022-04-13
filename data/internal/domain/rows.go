package domain

import (
	"time"

	"github.com/WLM1ke/gomoex"
)

// NewDayEndedID создает ID события окончания дня (необязательно торгового).
//
// Окончания дня привязано к моменту публикации итогов торгов.
func NewDayEndedID() ID {
	return NewID("day_ended", "day_ended")
}

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

// NewDateID создает ID информации о торговых днях.
func NewDateID() ID {
	return NewID("dates", "dates")
}

// NewIndexID создает ID индексов.
func NewIndexID(index string) ID {
	return NewID("indexes", index)
}

// NewUsdID создает ID курса доллара.
func NewUsdID() ID {
	return NewID("usd", "usd")
}

// NewSecuritiesID создает ID информации о торгующихся тикерах.
func NewSecuritiesID() ID {
	return NewID("securities", "securities")
}

// QuotesGroup - группа таблиц с котировками.
const QuotesGroup = "quotes"

// NewQuotesID создает ID котировок тикера.
func NewQuotesID(ticker string) ID {
	return NewID(QuotesGroup, ticker)
}

// CPI - месячные данные об инфляции.
type CPI struct {
	Date  time.Time
	Value float64
}

// NewCpiID создает ID информации о месячной инфляции.
func NewCpiID() ID {
	return NewID("cpi", "cpi")
}

// Position - для которого нужно отслеживать статус дивидендов.
type Position string

// NewPositionsID создает ID информации о тикерах в портфеле.
func NewPositionsID() ID {
	return NewID("port", "port")
}

// DivStatus - информация об ожидаемых датах выплаты дивидендов.
type DivStatus struct {
	Ticker string
	Date   time.Time
}

// NewDivStatusID создает ID информации о новых дивидендах.
func NewDivStatusID() ID {
	return NewID("status", "status")
}

// RawDiv - введенные вручную данные о дивидендах с указанием валюты выплаты.
type RawDiv struct {
	Date     time.Time
	Value    float64
	Currency string
}

const (
	// USDCurrency - наименование валюты доллара.
	USDCurrency = `USD`
	// RURCurrency - наименование валюты рубля.
	RURCurrency = `RUR`
	// RawDivGroup - группа таблиц с вручную введенными дивидендами.
	RawDivGroup = `raw_div`
)

// NewRawDivID создает ID вручную введенных дивидендов тикера.
func NewRawDivID(ticker string) ID {
	return NewID(RawDivGroup, ticker)
}

// Dividend - данные о дивидендах переведенные в рубли и объединенные при нескольких выплатах в одну дату.
type Dividend struct {
	Date  time.Time
	Value float64
}

// NewDividendsID создает ID дивидендов тикера.
func NewDividendsID(ticker string) ID {
	return NewID("dividends", ticker)
}

// Row - строки данных в таблицах.
type Row interface {
	Date | CPI | Index | USD | Security | Position | DivStatus | RawDiv | Dividend
}
