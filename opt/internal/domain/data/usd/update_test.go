package usd

import (
	"context"
	"testing"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/mocks"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestHandler_Update(t *testing.T) {
	t.Parallel()

	candles := []gomoex.Candle{
		{
			Begin:  time.Date(2022, time.June, 1, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   1,
			Close:  2,
			High:   3,
			Low:    4,
			Value:  5,
			Volume: 6,
		},
		{
			Begin:  time.Date(2022, time.June, 2, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   3,
			Close:  4,
			High:   5,
			Low:    6,
			Value:  7,
			Volume: 8,
		},
		{
			Begin:  time.Date(2022, time.June, 4, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   4,
			Close:  5,
			High:   6,
			Low:    7,
			Value:  8,
			Volume: 9,
		},
	}
	tradingDay := time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		mocks.NewAgg[Table](
			ID(),
			time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			convert(candles[:2]),
		), nil).
		On("Save", mocks.NewAgg[Table](ID(), tradingDay, convert(candles))).
		Return(nil)

	iss := new(mocks.ISS)
	iss.On(
		"MarketCandles",
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		"2022-06-02",
		"2022-06-26",
		gomoex.IntervalDay,
	).Return(candles[1:], nil)

	service := NewService(lgr.Discard(), repo, iss)

	assert.Equal(t, convert(candles), service.Update(context.Background(), tradingDay))
	mock.AssertExpectationsForObjects(t, repo, iss)
}

func TestHandler_Update_FirstLoad(t *testing.T) {
	t.Parallel()

	candles := []gomoex.Candle{
		{
			Begin:  time.Date(2022, time.June, 1, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   1,
			Close:  2,
			High:   3,
			Low:    4,
			Value:  5,
			Volume: 6,
		},
		{
			Begin:  time.Date(2022, time.June, 2, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   3,
			Close:  4,
			High:   5,
			Low:    6,
			Value:  7,
			Volume: 8,
		},
	}
	tradingDay := time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(mocks.NewEmptyAgg[Table](ID()), nil).
		On("Save", mocks.NewAgg[Table](ID(), tradingDay, convert(candles))).Return(nil)

	iss := new(mocks.ISS)
	iss.On(
		"MarketCandles",
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		"",
		"2022-06-26",
		gomoex.IntervalDay,
	).Return(candles, nil)

	service := NewService(lgr.Discard(), repo, iss)

	assert.Equal(t, convert(candles), service.Update(context.Background(), tradingDay))
	mock.AssertExpectationsForObjects(t, repo, iss)
}

func TestHandler_UpdateEmpty(t *testing.T) {
	t.Parallel()

	candles := []gomoex.Candle{
		{
			Begin:  time.Date(2022, time.June, 1, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   1,
			Close:  2,
			High:   3,
			Low:    4,
			Value:  5,
			Volume: 6,
		},
		{
			Begin:  time.Date(2022, time.June, 2, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   3,
			Close:  4,
			High:   5,
			Low:    6,
			Value:  7,
			Volume: 8,
		},
		{
			Begin:  time.Date(2022, time.June, 4, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   4,
			Close:  5,
			High:   6,
			Low:    7,
			Value:  8,
			Volume: 9,
		},
	}
	tradingDay := time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		mocks.NewAgg[Table](
			ID(),
			time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			convert(candles),
		), nil)

	iss := new(mocks.ISS)
	iss.On(
		"MarketCandles",
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		"2022-06-04",
		"2022-06-26",
		gomoex.IntervalDay,
	).Return(candles[2:], nil)

	service := NewService(lgr.Discard(), repo, iss)

	assert.Equal(t, convert(candles), service.Update(context.Background(), tradingDay))

	mock.AssertExpectationsForObjects(t, repo, iss)
}

func TestHandler_HandleNotIncreasing(t *testing.T) {
	t.Parallel()

	candles := []gomoex.Candle{
		{
			Begin:  time.Date(2022, time.June, 1, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   1,
			Close:  2,
			High:   3,
			Low:    4,
			Value:  5,
			Volume: 6,
		},
		{
			Begin:  time.Date(2022, time.June, 2, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   3,
			Close:  4,
			High:   5,
			Low:    6,
			Value:  7,
			Volume: 8,
		},
		{
			Begin:  time.Date(2022, time.January, 4, 0, 0, 0, 0, time.UTC),
			End:    time.Time{},
			Open:   4,
			Close:  5,
			High:   6,
			Low:    7,
			Value:  8,
			Volume: 9,
		},
	}
	tradingDay := time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		mocks.NewAgg[Table](
			ID(),
			time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			convert(candles[:2]),
		), nil)

	iss := new(mocks.ISS)
	iss.On(
		"MarketCandles",
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		"2022-06-02",
		"2022-06-26",
		gomoex.IntervalDay,
	).Return(candles[1:], nil)

	service := NewService(lgr.Discard(), repo, iss)

	assert.Nil(t, service.Update(context.Background(), tradingDay))

	mock.AssertExpectationsForObjects(t, repo, iss)
}
