package trading

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const _tradingDateGroup = "trading_date"

// ID - id информации о последнем торговом дне.
func ID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _tradingDateGroup,
		ID:    _tradingDateGroup,
	}
}

// Date последнего обновления.
type Date = time.Time
