package cpi

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const _CPIGroup = `cpi`

// ID данных о месячной инфляции.
func ID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _CPIGroup,
		ID:    _CPIGroup,
	}
}

// CPI месячное изменение цен.
type CPI struct {
	Date  time.Time
	Value float64
}

// Table таблица с данными по инфляции.
type Table = data.Table[CPI]
