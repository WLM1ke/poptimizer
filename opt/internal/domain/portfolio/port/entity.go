package port

import (
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"golang.org/x/exp/slices"
)

const (
	_Group      = `portfolio`
	_NewAccount = `__new__`
)

// ID соответствующего портфеля.
func ID(account string) domain.QID {
	return domain.QID{
		Sub:   portfolio.Subdomain,
		Group: _Group,
		ID:    account,
	}
}

// Position представляет информацию об отдельной позиции.
type Position struct {
	Ticker   string
	Shares   int
	Lot      int
	Price    float64
	Turnover float64
	Selected bool
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
	Positions []Position
	Cash      float64
}

// Value стоимость портфеля.
func (p Portfolio) Value() float64 {
	sum := p.Positions[0].Value()

	for _, pos := range p.Positions[1:] {
		sum += pos.Value()
	}

	return sum + p.Cash
}

// Sum создает новый портфель с суммарным объемом позиций и денег в двух портфелях.
func (p Portfolio) Sum(other Portfolio) Portfolio {
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

// UpdateSec обновляет информацию об лотах и выбранных бумагах.
//
// Обновляются размеры лотов и проверяется, что на нем находятся только выбранные бумаги и количество лотов целое.
func (p *Portfolio) UpdateSec(sec securities.Table, newDay bool) []error {
	positions := p.copyAndResetPositions(newDay)

	nPos := 0
	nSec := 0

	for nPos < len(positions) && nSec < len(sec) {
		posCurrent := positions[nPos]
		secCurrent := sec[nSec]

		switch {
		case posCurrent.Ticker < secCurrent.Ticker:
			p.Positions = append(p.Positions, posCurrent)

			nPos++
		case posCurrent.Ticker > secCurrent.Ticker:
			if secCurrent.Selected {
				p.Positions = append(p.Positions, Position{
					Ticker:   secCurrent.Ticker,
					Shares:   0,
					Lot:      secCurrent.Lot,
					Price:    0,
					Turnover: 0,
					Selected: true,
				})
			}

			nSec++
		case posCurrent.Ticker == secCurrent.Ticker:
			if secCurrent.Selected || posCurrent.Shares != 0 {
				posCurrent.Lot = secCurrent.Lot
				posCurrent.Selected = secCurrent.Selected

				p.Positions = append(p.Positions, posCurrent)
			}

			nPos++
			nSec++
		}
	}

	p.leftSec(sec[nSec:])

	p.leftPositions(positions[nPos:])

	return p.validatePositions()
}

func (p *Portfolio) copyAndResetPositions(newDay bool) []Position {
	positions := slices.Clone(p.Positions)
	p.Positions = p.Positions[:0]

	if !newDay {
		return positions
	}

	for _, pos := range positions {
		pos.Turnover = 0
		pos.Selected = false
	}

	return positions
}

func (p *Portfolio) leftSec(sec securities.Table) {
	for _, security := range sec {
		if !security.Selected {
			continue
		}

		p.Positions = append(p.Positions, Position{
			Ticker:   security.Ticker,
			Shares:   0,
			Lot:      security.Lot,
			Price:    0,
			Turnover: 0,
			Selected: true,
		})
	}
}

func (p *Portfolio) leftPositions(positions []Position) {
	p.Positions = append(p.Positions, positions...)
}

func (p Portfolio) validatePositions() (errs []error) {
	for _, pos := range p.Positions {
		if pos.Shares%pos.Lot != 0 {
			errs = append(errs, fmt.Errorf("%s have fractional lots", pos.Ticker))
		}

		if !pos.Selected {
			errs = append(errs, fmt.Errorf("%s not selected", pos.Ticker))
		}
	}

	return errs
}
