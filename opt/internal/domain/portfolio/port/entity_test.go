package port

import (
	"testing"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/stretchr/testify/assert"
)

func TestPosition(t *testing.T) {
	t.Parallel()

	pos := Position{
		Shares: 2,
		Price:  3,
	}

	assert.Equal(t, 6.0, pos.Value(), "incorrect position value")
	assert.Equal(t, 0.6, pos.Weight(10), "incorrect position weight")
}

func TestPosition_Value(t *testing.T) {
	t.Parallel()

	pos := []Position{
		{Shares: 1, Price: 2},
		{Shares: 3, Price: 4},
	}

	port := Portfolio{
		Positions: pos,
		Cash:      5,
	}

	assert.Equal(t, 19.0, port.Value(), "incorrect portfolio value")
}

func TestPortfolio_Sum(t *testing.T) {
	t.Parallel()

	pos1 := Position{Ticker: "AKRN", Shares: 1, Lot: 10, Price: 2, Turnover: 11, Selected: false}
	pos21 := Position{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 4, Selected: true}
	pos22 := Position{Ticker: "GAZP", Shares: 3, Lot: 100, Price: 5, Turnover: 4, Selected: true}
	pos2Sum := Position{Ticker: "GAZP", Shares: 5, Lot: 100, Price: 5, Turnover: 4, Selected: true}
	pos3 := Position{Ticker: "TRUR", Shares: 4, Lot: 100, Price: 6, Turnover: 4, Selected: true}

	port1 := Portfolio{
		Positions: []Position{pos1, pos21},
		Cash:      13,
	}
	port2 := Portfolio{
		Positions: []Position{pos22, pos3},
		Cash:      25,
	}
	portSum := Portfolio{
		Positions: []Position{pos1, pos2Sum, pos3},
		Cash:      38,
	}

	assert.Equal(t, portSum, port1.Sum(port2))
	assert.Equal(t, portSum, port2.Sum(port1))
}

func TestPortfolio_UpdateSecOldDay(t *testing.T) {
	t.Parallel()

	port := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 2, Turnover: 11, Selected: true},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 4, Selected: false},
		},
		Cash: 111,
	}

	sec := securities.Table{
		{Ticker: "GAZP", Lot: 10, Selected: true},
		{Ticker: "TRUR", Lot: 100, Selected: false},
		{Ticker: "UPRO", Lot: 1, Selected: true},
	}

	rez := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 2, Turnover: 11, Selected: true},
			{Ticker: "GAZP", Shares: 2, Lot: 10, Price: 5, Turnover: 4, Selected: true},
			{Ticker: "UPRO", Shares: 0, Lot: 1, Price: 0, Turnover: 0, Selected: true},
		},
		Cash: 111,
	}

	errs := port.UpdateSec(sec, false)

	assert.Len(t, errs, 1)
	assert.ErrorContains(t, errs[0], "GAZP have fractional lots")
	assert.Equal(t, rez, port, "wrong portfolio update for old day")
}

func TestPortfolio_UpdateSecNewDay(t *testing.T) {
	t.Parallel()

	port := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 2, Turnover: 11, Selected: true},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 4, Selected: false},
			{Ticker: "VSMO", Shares: 0, Lot: 1, Price: 9, Turnover: 11, Selected: true},
			{Ticker: "ZZZZ", Shares: 23, Lot: 1, Price: 9, Turnover: 11, Selected: true},
		},
		Cash: 111,
	}

	sec := securities.Table{
		{Ticker: "GAZP", Lot: 10, Selected: true},
		{Ticker: "TRUR", Lot: 100, Selected: false},
		{Ticker: "UPRO", Lot: 1, Selected: true},
	}

	rez := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 2, Turnover: 0, Selected: false},
			{Ticker: "GAZP", Shares: 2, Lot: 10, Price: 5, Turnover: 0, Selected: true},
			{Ticker: "UPRO", Shares: 0, Lot: 1, Price: 0, Turnover: 0, Selected: true},
			{Ticker: "ZZZZ", Shares: 23, Lot: 1, Price: 9, Turnover: 0, Selected: false},
		},
		Cash: 111,
	}

	errs := port.UpdateSec(sec, true)

	assert.Len(t, errs, 3)
	assert.ErrorContains(t, errs[0], "AKRN not selected")
	assert.ErrorContains(t, errs[1], "GAZP have fractional lots")
	assert.ErrorContains(t, errs[2], "ZZZZ not selected")
	assert.Equal(t, rez, port, "wrong portfolio update for old day")
}

func TestPortfolio_UpdateMarketData(t *testing.T) {
	t.Parallel()

	port := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 2, Turnover: 11, Selected: true},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 4, Selected: false},
		},
		Cash: 111,
	}

	port.UpdateMarketData("AKRN", 3, 10, false)

	port1 := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 3, Turnover: 10, Selected: true},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 4, Selected: false},
		},
		Cash: 111,
	}

	assert.Equal(t, port1, port)

	port.UpdateMarketData("B", 4, 40, true)

	port2 := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 3, Turnover: 0, Selected: false},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 0, Selected: false},
		},
		Cash: 111,
	}

	assert.Equal(t, port2, port)

	port.UpdateMarketData("AKRN", 8, 10, false)
	port.UpdateMarketData("Z", 4, 40, false)

	port3 := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10, Price: 8, Turnover: 10, Selected: false},
			{Ticker: "GAZP", Shares: 2, Lot: 100, Price: 5, Turnover: 0, Selected: false},
		},
		Cash: 111,
	}

	assert.Equal(t, port3, port)
}

func TestService_SetAmount(t *testing.T) {
	t.Parallel()

	port := Portfolio{
		Positions: []Position{
			{Ticker: "AKRN", Shares: 10, Lot: 10},
			{Ticker: "GAZP", Shares: 2, Lot: 100},
		},
		Cash: 111,
	}

	assert.ErrorContains(t, port.SetAmount("AKRN", -10), "amount must be positive")

	assert.Nil(t, port.SetAmount("CASH", 10))
	assert.Equal(t, 10, port.Cash)

	assert.ErrorContains(t, port.SetAmount("B", 20), "not found in portfolio")
	assert.ErrorContains(t, port.SetAmount("Z", 20), "not found in portfolio")

	assert.ErrorContains(t, port.SetAmount("GAZP", 20), "amount have fractional lots")

	assert.Nil(t, port.SetAmount("GAZP", 200))
}
