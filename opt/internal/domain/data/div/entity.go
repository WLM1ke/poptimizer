package div

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

// _DivGroup - группа дивидендов, пересчитанных в рубли.
const _DivGroup = "dividends"

// ID дивидендов, пересчитанных в рубли.
func ID(ticker string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _DivGroup,
		ID:    ticker,
	}
}

// Dividend данные о выплате дивидендов, пересчитанных в рубли.
type Dividend struct {
	Date  time.Time
	Value float64
}

// Table - таблица со всеми выплаченными дивидендами, пересчитанными в рубли.
type Table = data.Table[Dividend]
