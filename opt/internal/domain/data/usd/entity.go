package usd

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

// _USDGroup группа и id данных курсе доллара.
const _USDGroup = "usd"

// ID котировок курса доллара.
func ID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _USDGroup,
		ID:    _USDGroup,
	}
}

// USD свечка с данными о курсе доллара.
type USD struct {
	Date     time.Time
	Open     float64
	Close    float64
	High     float64
	Low      float64
	Turnover float64
}

// Table с котировками курса доллар.
type Table = data.Table[USD]
