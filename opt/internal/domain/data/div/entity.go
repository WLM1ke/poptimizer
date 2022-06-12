package div

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const (
	// RawGroup группа и id введенных пользователем дивидендов.
	RawGroup = `raw_div`
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

// Raw представляет дивиденды не конвертированные в валюту расчетов.
type Raw struct {
	Date     time.Time
	Value    float64
	Currency string
}

// RawTable таблица с данными о дивидендах до пересчета в рубли.
type RawTable = data.Table[Raw]
