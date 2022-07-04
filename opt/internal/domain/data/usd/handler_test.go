package usd

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/dates"
	"github.com/WLM1ke/poptimizer/opt/internal/mocks"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestHandler_Match(t *testing.T) {
	t.Parallel()

	table := []struct {
		event domain.Event
		match bool
	}{
		{
			event: domain.Event{
				QID:  dates.ID(),
				Data: nil,
			},
			match: true,
		},
		{
			event: domain.Event{
				QID:  dates.ID(),
				Data: 42,
			},
			match: false,
		},
		{
			event: domain.Event{
				QID:  ID(),
				Data: nil,
			},
			match: false,
		},
	}

	handler := NewHandler(new(mocks.Pub), new(mocks.Repo[Table]), new(mocks.ISS))

	for _, test := range table {
		assert.Equal(t, test.match, handler.Match(test.event), "incorrect event match")
	}
}

func TestHandler_HandleFirstLoad(t *testing.T) {
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

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(domain.Aggregate[Table]{}, nil).
		On("Append", domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles),
		}).Return(nil)

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

	pub := new(mocks.Pub)
	pub.On("Publish",
		domain.Event{
			QID:       ID(),
			Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
			Data:      convert(candles),
		},
	)

	handler := NewHandler(pub, repo, iss)

	handler.Handle(context.Background(), domain.Event{
		QID:       ID(),
		Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
		Data:      nil,
	})

	mock.AssertExpectationsForObjects(t, pub, repo, iss)
}

func TestHandler_HandleUpdate(t *testing.T) {
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

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles[:2]),
		}, nil).
		On("Append", domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles[2:]),
		}).Return(nil)

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

	pub := new(mocks.Pub)
	pub.On("Publish",
		domain.Event{
			QID:       ID(),
			Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
			Data:      convert(candles),
		},
	)

	handler := NewHandler(pub, repo, iss)

	handler.Handle(context.Background(), domain.Event{
		QID:       ID(),
		Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
		Data:      nil,
	})

	mock.AssertExpectationsForObjects(t, pub, repo, iss)
}

func TestHandler_HandleUpdateEmpty(t *testing.T) {
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

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles),
		}, nil)

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

	pub := new(mocks.Pub)

	handler := NewHandler(pub, repo, iss)

	handler.Handle(context.Background(), domain.Event{
		QID:       ID(),
		Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
		Data:      nil,
	})

	mock.AssertExpectationsForObjects(t, pub, repo, iss)
}

func TestHandler_HandleNotMatch(t *testing.T) {
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

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles[:2]),
		}, nil)

	iss := new(mocks.ISS)
	iss.On(
		"MarketCandles",
		gomoex.EngineCurrency,
		gomoex.MarketSelt,
		_usdTicker,
		"2022-06-02",
		"2022-06-26",
		gomoex.IntervalDay,
	).Return(candles, nil)

	pub := new(mocks.Pub)
	pub.On("Publish", mock.MatchedBy(func(event domain.Event) bool {
		return event.QID == ID() &&
			event.Timestamp.Equal(
				time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)) &&
			strings.Contains(event.Data.(error).Error(), "not match")
	}),
	)

	handler := NewHandler(pub, repo, iss)

	handler.Handle(context.Background(), domain.Event{
		QID:       ID(),
		Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
		Data:      nil,
	})

	mock.AssertExpectationsForObjects(t, pub, repo, iss)
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

	repo := new(mocks.Repo[Table])
	repo.On("Get", ID()).Return(
		domain.Aggregate[Table]{
			Timestamp: time.Date(2022, time.June, 25, 0, 0, 0, 0, time.UTC),
			Entity:    convert(candles[:2]),
		}, nil)

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

	pub := new(mocks.Pub)
	pub.On("Publish", mock.MatchedBy(func(event domain.Event) bool {
		return event.QID == ID() &&
			event.Timestamp.Equal(
				time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC)) &&
			strings.Contains(event.Data.(error).Error(), "not increasing dates")
	}),
	)

	handler := NewHandler(pub, repo, iss)

	handler.Handle(context.Background(), domain.Event{
		QID:       ID(),
		Timestamp: time.Date(2022, time.June, 26, 0, 0, 0, 0, time.UTC),
		Data:      nil,
	})

	mock.AssertExpectationsForObjects(t, pub, repo, iss)
}
