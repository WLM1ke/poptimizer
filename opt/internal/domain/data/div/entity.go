package div

import (
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"time"
)

// Raw представляет дивиденды не конвертированные в валюту расчетов.
type Raw struct {
	Date     time.Time
	Value    float64
	Currency string
}

type TableRaw = data.Table[Raw]
