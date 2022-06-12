package div

import (
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const (
	_rawGroup          = `raw_div`
	_closeReestryGroup = `close_reestry`
	_NASDAQGroup       = `nasdaq`

	// USDCurrency - наименование валюты доллара.
	USDCurrency = `USD`
	// RURCurrency - наименование валюты рубля.
	RURCurrency = `RUR`

	_eventDateFormat = `2006-01-02`
)

// StatusID информации о статусе дивидендов.
func StatusID(ticker string) domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: _statusGroup,
		ID:    ticker,
	}
}

// Status - информация об ожидаемых датах выплаты дивидендов.
type Status struct {
	Ticker     string
	BaseTicker string
	Preferred  bool
	Foreign    bool
	Date       time.Time
}

// StatusTable таблица со статусом дивидендов.
type StatusTable = data.Table[Status]

// RawID - id введенных пользователем данных о дивидендах.
func RawID(ticker string) domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: _rawGroup,
		ID:    ticker,
	}
}

// CloseReestryID - id данных о дивидендах с закрытияреестров.рф.
func CloseReestryID(ticker string) domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: _closeReestryGroup,
		ID:    ticker,
	}
}

// NASDAQid - id данных о дивидендах с NASDAQ.
func NASDAQid(ticker string) domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: _NASDAQGroup,
		ID:    ticker,
	}
}

// Raw представляет дивиденды не конвертированные в валюту расчетов.
type Raw struct {
	Date     time.Time
	Value    float64
	Currency string
}

// RawTable таблица с данными о дивидендах до пересчета в рубли.
type RawTable data.Table[Raw]

// Exists проверяет наличие дивидендов с указанной датой.
func (t RawTable) Exists(date time.Time) bool {
	n := sort.Search(
		len(t),
		func(i int) bool { return !t[i].Date.Before(date) },
	)

	return n < len(t) && t[n].Date.Equal(date)
}
