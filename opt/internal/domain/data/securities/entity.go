package securities

import (
	"sort"
	"strings"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
)

const (
	_group = "securities"

	_preferredType   = `2`
	_preferredSuffix = `P`

	_foreignBoard  = `FQBR`
	_foreignSuffix = `-RM`
)

// ID информации о торгуемых бумагах в целом.
func ID() domain.QID {
	return domain.QID{
		Sub:   data.Subdomain,
		Group: _group,
		ID:    _group,
	}
}

// Security описание бумаги.
type Security struct {
	Ticker     string
	Lot        int
	ISIN       string
	Board      string
	Type       string
	Instrument string
	Selected   bool
}

// IsPreferred является ли бумага привилегированной акцией.
func (s Security) IsPreferred() bool {
	return s.Type == _preferredType
}

// IsForeign является ли бумага иностранной акцией.
func (s Security) IsForeign() bool {
	return s.Board == _foreignBoard
}

// BaseTicker выдает тикер без суффикса привилегированной или иностранной бумаги.
func (s Security) BaseTicker() string {
	switch {
	case s.IsPreferred():
		return strings.TrimSuffix(s.Ticker, _preferredSuffix)
	case s.IsForeign():
		return strings.TrimSuffix(s.Ticker, _foreignSuffix)
	default:
		return s.Ticker
	}
}

// Table таблица с данными о торгуемых бумагах.
type Table []Security

func (t Table) update(raw []gomoex.Security) Table {
	table := make(Table, 0, len(raw))

	for _, row := range raw {
		sec, ok := t.Get(row.Ticker)

		table = append(table, Security{
			Selected:   sec.Selected && ok,
			Ticker:     row.Ticker,
			Lot:        row.LotSize,
			ISIN:       row.ISIN,
			Board:      row.Board,
			Type:       row.Type,
			Instrument: row.Instrument,
		})
	}

	sort.Slice(table, func(i, j int) bool { return table[i].Ticker < table[j].Ticker })

	return table
}

// Get получает описание бумаги для тикера и статус наличия такой бумаги.
func (t Table) Get(ticker string) (Security, bool) {
	n := sort.Search(len(t), func(i int) bool { return t[i].Ticker >= ticker })
	if n < len(t) && t[n].Ticker == ticker {
		return t[n], true
	}

	return Security{}, false
}
