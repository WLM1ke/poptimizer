package account

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

const (
	_Group      = `accounts`
	_NewAccount = `__new__`
	// RUR - тикер рублевой позиции.
	RUR = `RUR`
)

// GroupID - id сводной информации об брокерских счетах.
func GroupID() domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _Group,
		ID:    _Group,
	}
}

// ID соответствующего брокерского счета.
func ID(account string) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _Group,
		ID:    account,
	}
}

// Position представляет информацию о количестве акций и размере лота.
type Position struct {
	Shares int
	Lot    int
}

// Account - пары тикер-позиция.
type Account map[string]Position

// Sum создает новый счет с суммарным объемом позиций на двух счетах.
func (a Account) Sum(acc Account) Account {
	newAcc := make(Account, len(acc))

	for ticker, pos := range acc {
		newAcc[ticker] = pos
	}

	for ticker, pos := range a {
		current := newAcc[ticker]
		current.Shares += pos.Shares
		current.Lot = pos.Lot

		newAcc[ticker] = current
	}

	return newAcc
}

// Update обновляет данные счета.
//
// Для нового счета создается нулевая позиция в рублях. Для любого счета обновляются размеры лотов и проверяется, что
// на нем находятся только выбранные бумаги и количество лотов целое.
func (a *Account) Update(table securities.Table) (errs []error) {
	if len(*a) == 0 {
		*a = make(map[string]Position)
		(*a)[RUR] = Position{
			Shares: 0,
			Lot:    1,
		}
	}

	old := make(map[string]Position, len(*a))

	for ticker, pos := range *a {
		if ticker == RUR {
			continue
		}

		old[ticker] = pos

		delete(*a, ticker)
	}

	for _, sec := range table {
		if !sec.Selected {
			continue
		}

		ticker := sec.Ticker

		pos := old[ticker]
		delete(old, ticker)

		pos.Lot = sec.Lot
		(*a)[ticker] = pos

		if pos.Shares%pos.Lot != 0 {
			errs = append(errs, fmt.Errorf("fractional lots for %s", ticker))
		}
	}

	for ticker, pos := range old {
		if pos.Shares == 0 {
			continue
		}

		errs = append(errs, fmt.Errorf("not selected ticker %s", ticker))

		(*a)[ticker] = pos
	}

	return errs
}
