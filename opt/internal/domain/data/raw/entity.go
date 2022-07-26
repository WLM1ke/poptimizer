package raw

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
)

// StatusID информации о статусе дивидендов.
func StatusID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _statusGroup,
		ID:    _statusGroup,
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

// ID введенных пользователем данных о дивидендах.
func ID(ticker string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _rawGroup,
		ID:    ticker,
	}
}

// ReestryID данных о дивидендах с закрытияреестров.рф.
func ReestryID(ticker string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _closeReestryGroup,
		ID:    ticker,
	}
}

// NasdaqID данных о дивидендах с NASDAQ.
func NasdaqID(ticker string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _NASDAQGroup,
		ID:    ticker,
	}
}

// Raw представляет дивиденды не конвертированные в валюту расчетов.
type Raw struct {
	Date     time.Time `json:"date"`
	Value    float64   `json:"value"`
	Currency string    `json:"currency"`
}

// ValidDate проверяет, что дата находится после начала сбора статистики по дивидендам.
func (r Raw) ValidDate() bool {
	return domain.DataStartDate().Before(r.Date)
}

// Table таблица с данными о дивидендах до пересчета в рубли.
type Table data.Table[Raw]

// Sort сортирует строки.
func (t Table) Sort() {
	sort.Slice(t, func(i, j int) bool {
		return t[i].Date.Before(t[j].Date) ||
			t[i].Date.Equal(t[j].Date) && t[i].Value < t[j].Value ||
			t[i].Date.Equal(t[j].Date) && t[i].Value == t[j].Value && t[i].Currency < t[j].Currency
	})
}

// ExistsDate проверяет наличие дивидендов с указанной датой.
func (t Table) ExistsDate(date time.Time) bool {
	n := sort.Search(
		len(t),
		func(i int) bool { return !t[i].Date.Before(date) },
	)

	return n < len(t) && t[n].Date.Equal(date)
}

// Exists проверяет, что данная запись о дивидендах существует.
func (t Table) Exists(raw Raw) bool {
	foundPos := sort.Search(
		len(t),
		func(pos int) bool {
			value := t[pos]

			return value.Date.After(raw.Date) ||
				(value.Date.Equal(raw.Date) && value.Value > raw.Value) ||
				(value.Date.Equal(raw.Date) && value.Value == raw.Value && value.Currency >= raw.Currency)
		},
	)

	if foundPos >= len(t) {
		return false
	}

	return t[foundPos].Date.Equal(raw.Date) && t[foundPos].Value == raw.Value && t[foundPos].Currency == raw.Currency
}
