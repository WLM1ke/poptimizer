package port

import (
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"golang.org/x/exp/slices"
)

const (
	_AccountsGroup  = `accounts`
	_PortfolioGroup = `portfolio`
	_portIDLayout   = `2006-01-02`
	_NewAccount     = `__new__`
	_Cash           = `CASH`
)

// AccountID соответствующего брокерского счета.
func AccountID(account string) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _AccountsGroup,
		ID:    account,
	}
}

// PortfolioDateID портфеля на соответствующую дату.
func PortfolioDateID(date time.Time) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _PortfolioGroup,
		ID:    date.Format(_portIDLayout),
	}
}

// PortfolioID портфеля на соответствующую дату.
func PortfolioID(date string) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _PortfolioGroup,
		ID:    date,
	}
}

// Position представляет информацию об отдельной позиции.
type Position struct {
	Ticker   string  `json:"ticker"`
	Shares   int     `json:"shares"`
	Lot      int     `json:"lot"`
	Price    float64 `json:"price"`
	Turnover float64 `json:"turnover"`
}

// Value стоимость позиции.
func (p Position) Value() float64 {
	return p.Price * float64(p.Shares)
}

// Weight вес позиции для заданной стоимости портфеля.
func (p Position) Weight(total float64) float64 {
	return p.Value() / total
}

// Portfolio - портфель, состоящий из позиций и денежных средств.
type Portfolio struct {
	Positions []Position `json:"positions"`
	Cash      int        `json:"cash"`
}

// Value стоимость портфеля.
func (p Portfolio) Value() float64 {
	value := float64(p.Cash)

	for _, pos := range p.Positions {
		value += pos.Value()
	}

	return value
}

// Сбрасываются рыночные данные и обновляется перечень бумаг с учетом новых выбранных. Если на счету есть не выбранные
// бумаги или бумаги с дробным лотом, то возвращаются ошибки.
func (p *Portfolio) updateSec(sec securities.Table) (errs []error) {
	positions := slices.Clone(p.Positions)
	p.Positions = p.Positions[:0]

	nPos := 0
	nSec := 0

	for nPos < len(positions) && nSec < len(sec) {
		posCurrent := Position{
			Ticker: positions[nPos].Ticker,
			Shares: positions[nPos].Shares,
		}
		secCurrent := sec[nSec]

		switch {
		case posCurrent.Shares == 0:
			nPos++
		case posCurrent.Ticker < secCurrent.Ticker:
			p.Positions = append(p.Positions, posCurrent)
			errs = append(errs, fmt.Errorf("%s not selected", posCurrent.Ticker))

			nPos++
		case posCurrent.Ticker > secCurrent.Ticker:
			if secCurrent.Selected {
				p.Positions = append(p.Positions, Position{
					Ticker: secCurrent.Ticker,
					Lot:    secCurrent.Lot,
				})
			}

			nSec++
		case posCurrent.Ticker == secCurrent.Ticker:
			posCurrent.Lot = secCurrent.Lot
			p.Positions = append(p.Positions, posCurrent)

			if !secCurrent.Selected {
				errs = append(errs, fmt.Errorf("%s not selected", posCurrent.Ticker))
			}

			if posCurrent.Shares%secCurrent.Lot != 0 {
				errs = append(errs, fmt.Errorf("%s have fractional lots", posCurrent.Ticker))
			}

			nPos++
			nSec++
		}
	}

	p.leftSec(sec[nSec:])

	return append(errs, p.leftPositions(positions[nPos:])...)
}

func (p *Portfolio) leftSec(sec securities.Table) {
	for _, security := range sec {
		if !security.Selected {
			continue
		}

		p.Positions = append(p.Positions, Position{
			Ticker: security.Ticker,
			Lot:    security.Lot,
		})
	}
}

func (p *Portfolio) leftPositions(positions []Position) (errs []error) {
	for _, pos := range positions {
		if pos.Shares > 0 {
			p.Positions = append(p.Positions, Position{
				Ticker: pos.Ticker,
				Shares: pos.Shares,
			})

			errs = append(errs, fmt.Errorf("%s not selected", pos.Ticker))
		}
	}

	return errs
}

// Sum создает новый портфель с суммарным объемом позиций и денег в двух портфелях.
func (p Portfolio) sum(other Portfolio) Portfolio {
	positions := make([]Position, 0, len(p.Positions))

	nCurrent := 0
	nOther := 0

	for nCurrent < len(p.Positions) && nOther < len(other.Positions) {
		posCurrent := p.Positions[nCurrent]
		posOther := other.Positions[nOther]

		switch {
		case posCurrent.Ticker < posOther.Ticker:
			positions = append(positions, posCurrent)

			nCurrent++
		case posCurrent.Ticker > posOther.Ticker:
			positions = append(positions, posOther)

			nOther++
		case posCurrent.Ticker == posOther.Ticker:
			pos := posCurrent
			pos.Shares += posOther.Shares

			positions = append(positions, pos)

			nCurrent++
			nOther++
		}
	}

	if nCurrent < len(p.Positions) {
		positions = append(positions, p.Positions[nCurrent:]...)
	}

	if nOther < len(other.Positions) {
		positions = append(positions, other.Positions[nOther:]...)
	}

	return Portfolio{
		Positions: positions,
		Cash:      p.Cash + other.Cash,
	}
}

// UpdateMarketData обновляет цену и оборот всех позиций.
func (p *Portfolio) updateMarketData(cache map[string]markerData) {
	for n := range p.Positions {
		data := cache[p.Positions[n].Ticker]
		p.Positions[n].Price = data.Price
		p.Positions[n].Turnover = data.Turnover
	}
}

// SetAmount меняет значение количества акций для заданного тикера.
//
// Для изменения количества денег необходимо указать тикер CASH.
func (p *Portfolio) SetAmount(ticker string, amount int) error {
	if amount < 0 {
		return fmt.Errorf("%d amount must be positive", amount)
	}

	if ticker == _Cash {
		p.Cash = amount

		return nil
	}

	pos := sort.Search(len(p.Positions), func(i int) bool { return p.Positions[i].Ticker >= ticker })
	if !(pos < len(p.Positions) && p.Positions[pos].Ticker == ticker) {
		return fmt.Errorf("%s not found in portfolio", ticker)
	}

	if amount%p.Positions[pos].Lot != 0 {
		return fmt.Errorf("%d amount have fractional lots %d for %s", amount, p.Positions[pos].Lot, ticker)
	}

	p.Positions[pos].Shares = amount

	return nil
}
