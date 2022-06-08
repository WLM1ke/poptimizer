package selected

import (
	"fmt"
	"strings"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"golang.org/x/exp/slices"
)

// ID выбранных для анализа тикеров.
func ID() domain.QualifiedID {
	return domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: Group,
		ID:    Group,
	}
}

// Tickers перечень тикеров, в том числе выбранных и не выбранных для анализа.
type Tickers map[string]bool

func (s Tickers) update(sec data.Rows[data.Security]) Tickers {
	tickers := make(Tickers, len(sec))

	for _, row := range sec {
		tickers[row.Ticker] = s[row.Ticker]
	}

	return tickers
}

// Selected выдает список выбранных тикеров.
func (s Tickers) Selected() []string {
	tickers := make([]string, 0, len(s))

	for ticker, selected := range s {
		if selected {
			tickers = append(tickers, ticker)
		}
	}

	slices.Sort(tickers)

	return tickers
}

// SearchNotSelected выдает список доступных не выбранных тикеров.
func (s Tickers) SearchNotSelected(prefix string) []string {
	if prefix == "" {
		return nil
	}

	prefix = strings.ToUpper(prefix)

	tickers := make([]string, 0, len(s))

	for ticker, selected := range s {
		if !selected && strings.HasPrefix(ticker, prefix) {
			tickers = append(tickers, ticker)
		}
	}

	slices.Sort(tickers)

	return tickers
}

// Add добавляет тикер в список выбранных.
func (s Tickers) Add(ticker string) error {
	if selected, ok := s[ticker]; ok && !selected {
		s[ticker] = true

		return nil
	}

	return fmt.Errorf("incorrect ticker to add - %s", ticker)
}

// Remove удаляет тикер из списка выбранных.
func (s Tickers) Remove(ticker string) error {
	if selected, ok := s[ticker]; ok && selected {
		s[ticker] = false

		return nil
	}

	return fmt.Errorf("incorrect ticker to remove - %s", ticker)
}
