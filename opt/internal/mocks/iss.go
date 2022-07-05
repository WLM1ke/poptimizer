package mocks

import (
	"context"

	"github.com/WLM1ke/gomoex"
	"github.com/stretchr/testify/mock"
)

type ISS struct {
	mock.Mock
}

func (m *ISS) MarketCandles(
	_ context.Context,
	engine string,
	market string,
	security string,
	from, till string,
	interval int,
) ([]gomoex.Candle, error) {
	args := m.Called(engine, market, security, from, till, interval)

	return args.Get(0).([]gomoex.Candle), args.Error(1)
}
