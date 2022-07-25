package index

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const _IndexesGroup = "indexes"

// ID свечек индексов.
func ID(index string) domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _IndexesGroup,
		ID:    index,
	}
}

// Index свечка с данными об индексе.
type Index struct {
	Date     time.Time
	Open     float64
	Close    float64
	High     float64
	Low      float64
	Turnover float64
}

// Table с котировками биржевого индекса.
type Table = data.Table[Index]
