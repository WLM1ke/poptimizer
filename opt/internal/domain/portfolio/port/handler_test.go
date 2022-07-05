package port

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/market"
	"github.com/WLM1ke/poptimizer/opt/internal/mocks"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestHandler_Match(t *testing.T) {
	t.Parallel()

	tests := []struct {
		event domain.Event
		match bool
	}{
		{domain.Event{
			QID:  securities.GroupID(),
			Data: securities.Table{},
		}, true},
		{domain.Event{
			QID:  securities.ID("some"),
			Data: securities.Table{},
		}, false},
		{domain.Event{
			QID:  securities.GroupID(),
			Data: 42,
		}, false},
		{domain.Event{
			QID:  market.ID("some"),
			Data: market.Data{},
		}, true},
		{domain.Event{
			QID:  market.ID("some"),
			Data: 42,
		}, false},
		{domain.Event{
			QID:  securities.GroupID(),
			Data: market.Data{},
		}, false},
	}

	handle := Handler{}

	for _, test := range tests {
		assert.Equal(t, test.match, handle.Match(test.event))
	}
}

func TestHandler_HandleSecurities(t *testing.T) {
	t.Parallel()

	pub := new(mocks.Pub)
	pub.On("Publish",
		domain.Event{
			Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
			Data:      fmt.Errorf("GAZP not selected"),
		}).Return()

	aggIn := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 55,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	aggOut := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "AKRN",
					Shares:   0,
					Lot:      10,
					Price:    0,
					Turnover: 0,
					Selected: true,
				},
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 0,
					Selected: false,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      10,
					Price:    44,
					Turnover: 0,
					Selected: true,
				},
			},
			Cash: 12,
		},
	}

	repo := new(mocks.Repo[Portfolio])
	repo.
		On("GetGroup", portfolio.Subdomain, _Group).
		Return([]domain.Aggregate[Portfolio]{aggIn}, nil).
		On("Save", aggOut).
		Return(nil)

	handler := NewHandler(pub, repo)

	event := domain.Event{
		QID:       securities.GroupID(),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Data: securities.Table{
			{Ticker: "AKRN", Lot: 10, Selected: true},
			{Ticker: "NLMK", Lot: 10, Selected: true},
			{Ticker: "UPRO", Lot: 100, Selected: false},
		},
	}

	handler.Handle(context.Background(), event)
	handler.Close()

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleSecuritiesSameDate(t *testing.T) {
	t.Parallel()

	pub := new(mocks.Pub)

	aggIn := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 55,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	aggOut := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "AKRN",
					Shares:   0,
					Lot:      10,
					Price:    0,
					Turnover: 0,
					Selected: true,
				},
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      10,
					Price:    44,
					Turnover: 55,
					Selected: true,
				},
			},
			Cash: 12,
		},
	}

	repo := new(mocks.Repo[Portfolio])
	repo.
		On("GetGroup", portfolio.Subdomain, _Group).
		Return([]domain.Aggregate[Portfolio]{aggIn}, nil).
		On("Save", aggOut).
		Return(nil)

	handler := NewHandler(pub, repo)

	event := domain.Event{
		QID:       securities.GroupID(),
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Data: securities.Table{
			{Ticker: "AKRN", Lot: 10, Selected: true},
			{Ticker: "NLMK", Lot: 10, Selected: true},
			{Ticker: "UPRO", Lot: 100, Selected: false},
		},
	}

	handler.Handle(context.Background(), event)
	handler.Close()

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleMarketData(t *testing.T) {
	t.Parallel()

	pub := new(mocks.Pub)

	aggIn := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 55,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	aggOut := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    33,
					Turnover: 11,
					Selected: false,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 0,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	repo := new(mocks.Repo[Portfolio])
	repo.
		On("GetGroup", portfolio.Subdomain, _Group).
		Return([]domain.Aggregate[Portfolio]{aggIn}, nil).
		On("Save", aggOut).
		Return(nil)

	handler := NewHandler(pub, repo)

	event := domain.Event{
		QID:       market.ID("GAZP"),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Data: market.Data{
			Price:    33,
			Turnover: 11,
		},
	}

	handler.Handle(context.Background(), event)
	handler.Close()

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleMarketSameDate(t *testing.T) {
	t.Parallel()

	pub := new(mocks.Pub)

	aggIn := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 55,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	aggOut := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    33,
					Turnover: 11,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    44,
					Turnover: 55,
					Selected: false,
				},
			},
			Cash: 12,
		},
	}

	repo := new(mocks.Repo[Portfolio])
	repo.
		On("GetGroup", portfolio.Subdomain, _Group).
		Return([]domain.Aggregate[Portfolio]{aggIn}, nil).
		On("Save", aggOut).
		Return(nil)

	handler := NewHandler(pub, repo)

	event := domain.Event{
		QID:       market.ID("GAZP"),
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Data: market.Data{
			Price:    33,
			Turnover: 11,
		},
	}

	handler.Handle(context.Background(), event)
	handler.Close()

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleMultiple(t *testing.T) {
	t.Parallel()

	pub := new(mocks.Pub)
	pub.On("Publish",
		domain.Event{
			Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
			Data:      fmt.Errorf("GAZP not selected"),
		}).Return()

	aggIn := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 3, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 33,
					Selected: true,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      100,
					Price:    13,
					Turnover: 55,
					Selected: true,
				},
			},
			Cash: 12,
		},
	}

	aggOut := domain.Aggregate[Portfolio]{
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Entity: Portfolio{
			Positions: []Position{
				{
					Ticker:   "AKRN",
					Shares:   0,
					Lot:      10,
					Price:    33,
					Turnover: 11,
					Selected: true,
				},
				{
					Ticker:   "GAZP",
					Shares:   10,
					Lot:      10,
					Price:    22,
					Turnover: 0,
					Selected: false,
				},
				{
					Ticker:   "NLMK",
					Shares:   200,
					Lot:      10,
					Price:    44,
					Turnover: 2,
					Selected: true,
				},
			},
			Cash: 12,
		},
	}

	repo := new(mocks.Repo[Portfolio])
	repo.
		On("GetGroup", portfolio.Subdomain, _Group).
		Return([]domain.Aggregate[Portfolio]{aggIn}, nil).
		On("Save", aggOut).
		Return(nil)

	handler := Handler{
		pub:    pub,
		repo:   repo,
		lock:   sync.RWMutex{},
		work:   make(chan domain.Event, 3),
		closed: make(chan struct{}),
	}

	event1 := domain.Event{
		QID:       securities.GroupID(),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Data: securities.Table{
			{Ticker: "AKRN", Lot: 10, Selected: true},
			{Ticker: "NLMK", Lot: 10, Selected: true},
		},
	}

	event2 := domain.Event{
		QID:       market.ID("NLMK"),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Data: market.Data{
			Price:    44,
			Turnover: 2,
		},
	}

	event3 := domain.Event{
		QID:       market.ID("AKRN"),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
		Data: market.Data{
			Price:    33,
			Turnover: 11,
		},
	}

	handler.Handle(context.Background(), event1)
	handler.Handle(context.Background(), event2)
	handler.Handle(context.Background(), event3)

	go handler.handleBuffer()

	time.Sleep(time.Second)

	handler.Close()

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleAfterStop(t *testing.T) {
	t.Parallel()

	event := domain.Event{
		QID:       securities.GroupID(),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
	}

	pub := new(mocks.Pub)
	pub.On("Publish", domain.Event{
		QID:       ID(_Group),
		Timestamp: event.Timestamp,
		Data:      fmt.Errorf("trying to handle %v with stopped handler", event),
	}).Return()

	repo := new(mocks.Repo[Portfolio])

	handler := NewHandler(pub, repo)
	handler.Close()

	handler.Handle(context.Background(), event)

	mock.AssertExpectationsForObjects(t, pub, repo)
}

func TestHandler_HandleAfterTimeout(t *testing.T) {
	t.Parallel()

	event := domain.Event{
		QID:       securities.GroupID(),
		Timestamp: time.Date(2022, time.July, 4, 0, 0, 0, 0, time.UTC),
	}

	pub := new(mocks.Pub)
	pub.On("Publish", domain.Event{
		QID:       ID(_Group),
		Timestamp: event.Timestamp,
		Data:      fmt.Errorf("timeout while handling %v", event),
	}).Return()

	repo := new(mocks.Repo[Portfolio])

	handler := Handler{
		pub:  pub,
		repo: repo,
		lock: sync.RWMutex{},
		work: make(chan domain.Event),
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	handler.Handle(ctx, event)

	mock.AssertExpectationsForObjects(t, pub, repo)
}
