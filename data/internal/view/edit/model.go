package edit

import (
	"time"

)

type model struct {
	id string

	Ticker string
	Rows   []domain.RawDiv
}

func (m *model) Last() domain.RawDiv {
	if len(m.Rows) > 0 {
		return m.Rows[len(m.Rows)-1]
	}

	return domain.RawDiv{
		Date:     time.Now(),
		Value:    1,
		Currency: "RUR",
	}
}

func (m *model) addRow(row domain.RawDiv) {
	m.Rows = append(m.Rows, row)
}
