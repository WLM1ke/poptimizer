package port

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/market"
)

const _timeout = time.Minute

// Handler обработчик событий, отвечающий за обновление портфелей.
type Handler struct {
	pub  domain.Publisher
	port domain.ReadGroupWriteRepo[Portfolio]
	data domain.ReadRepo[market.Data]

	lock     sync.RWMutex
	stopping bool

	work   chan domain.Event
	closed chan struct{}
}

// NewHandler создает обработчик для актуализации данных портфелей.
func NewHandler(
	pub domain.Publisher,
	portRepo domain.ReadGroupWriteRepo[Portfolio],
	dataRepo domain.ReadRepo[market.Data],
) *Handler {
	handler := Handler{
		pub:    pub,
		port:   portRepo,
		data:   dataRepo,
		lock:   sync.RWMutex{},
		work:   make(chan domain.Event),
		closed: make(chan struct{}),
	}

	go handler.handleBuffer()

	return &handler
}

// Match выбирает событие обновления перечня бумаг и рыночных данных.
func (h *Handler) Match(event domain.Event) bool {
	if _, ok := event.Data.(securities.Table); ok && event.QID == securities.GroupID() {
		return true
	}

	_, ok := event.Data.(market.Data)

	return ok && event.QID == market.ID(event.ID)
}

func (h *Handler) String() string {
	return "securities or market data -> portfolio"
}

// Handle реагирует на событие об обновлении перечня бумаг или рыночных данных и обновляет данные портфелей.
func (h *Handler) Handle(ctx context.Context, event domain.Event) {
	h.lock.RLock()
	defer h.lock.RUnlock()

	if h.stopping {
		h.pub.Publish(domain.Event{
			QID:       AccountID(_AccountsGroup),
			Timestamp: event.Timestamp,
			Data:      fmt.Errorf("trying to handle %v with stopped handler", event),
		})

		return
	}

	select {
	case h.work <- event:
	case <-ctx.Done():
		h.pub.Publish(domain.Event{
			QID:       AccountID(_AccountsGroup),
			Timestamp: event.Timestamp,
			Data:      fmt.Errorf("timeout while handling %v", event),
		})
	}
}

// Close завершает работу буферизированного обработчика.
func (h *Handler) Close() {
	h.lock.Lock()
	defer func() {
		h.lock.Unlock()
		<-h.closed
	}()

	h.stopping = true
	close(h.work)
}

func (h *Handler) handleBuffer() {
	defer close(h.closed)

	var aggs []domain.Aggregate[Portfolio]

	for {
		if len(aggs) == 0 {
			event, ok := <-h.work
			if !ok {
				return
			}

			aggs = h.handleEvent(event, aggs)

			continue
		}

		select {
		case event, ok := <-h.work:
			if !ok {
				h.save(aggs)

				return
			}

			aggs = h.handleEvent(event, aggs)
		default:
			h.save(aggs)
			aggs = nil
		}
	}
}

func (h *Handler) save(aggs []domain.Aggregate[Portfolio]) {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	portQID := PortfolioDateID(aggs[0].Timestamp)

	port, err := h.port.Get(ctx, portQID)
	if err != nil {
		h.pub.Publish(domain.Event{
			QID:       portQID,
			Timestamp: aggs[0].Timestamp,
			Data:      err,
		})

		return
	}

	port.Timestamp = aggs[0].Timestamp
	port.Entity = aggs[0].Entity

	for count, agg := range aggs {
		if err := h.port.Save(ctx, agg); err != nil {
			h.pub.Publish(domain.Event{
				QID:       agg.QID(),
				Timestamp: agg.Timestamp,
				Data:      err,
			})
		}

		if count == 0 {
			continue
		}

		port.Entity = port.Entity.Sum(agg.Entity)
	}

	err = h.port.Save(ctx, port)
	if err != nil {
		h.pub.Publish(domain.Event{
			QID:       port.QID(),
			Timestamp: port.Timestamp,
			Data:      err,
		})
	}
}

func (h *Handler) handleEvent(
	event domain.Event,
	aggs []domain.Aggregate[Portfolio],
) []domain.Aggregate[Portfolio] {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	aggs, err := h.loadAggs(ctx, aggs, event.Timestamp)
	if err != nil {
		event.QID = AccountID(_AccountsGroup)
		event.Data = err

		h.pub.Publish(event)

		return nil
	}

	switch data := event.Data.(type) {
	case securities.Table:
		h.updateSec(ctx, event, aggs, data)
	case market.Data:
		h.updateMarketData(event, aggs, data)
	default:
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)
	}

	return aggs
}

func (h *Handler) updateSec(
	ctx context.Context,
	event domain.Event,
	aggs []domain.Aggregate[Portfolio],
	data securities.Table,
) {
	for nAgg := range aggs {
		newDay := event.Timestamp.After(aggs[nAgg].Timestamp)
		if newDay {
			aggs[nAgg].Timestamp = event.Timestamp
		}

		event.QID = aggs[nAgg].QID()

		errs := aggs[nAgg].Entity.UpdateSec(data, newDay)
		if len(errs) != 0 {
			h.pubErr(event, errs)
		}

		if !newDay {
			h.updateMissedMarketData(ctx, aggs[nAgg])
		}
	}
}

func (h *Handler) updateMarketData(event domain.Event, aggs []domain.Aggregate[Portfolio], data market.Data) {
	for nAgg := range aggs {
		newDay := event.Timestamp.After(aggs[nAgg].Timestamp)
		if newDay {
			aggs[nAgg].Timestamp = event.Timestamp
		}

		ticker := event.ID
		aggs[nAgg].Entity.UpdateMarketData(ticker, data.Price, data.Turnover, newDay)
	}
}

func (h *Handler) loadAggs(
	ctx context.Context,
	aggs []domain.Aggregate[Portfolio],
	timestamp time.Time,
) ([]domain.Aggregate[Portfolio], error) {
	if aggs != nil {
		return aggs, nil
	}

	aggs, err := h.port.GetGroup(ctx, portfolio.Subdomain, _AccountsGroup)
	if err != nil {
		return nil, err
	}

	if len(aggs) > 0 {
		return aggs, nil
	}

	agg, err := h.port.Get(ctx, AccountID(_NewAccount))
	if err != nil {
		return nil, err
	}

	agg.Timestamp = timestamp

	return append(aggs, agg), nil
}

func (h *Handler) pubErr(event domain.Event, errs []error) {
	for _, err := range errs {
		event.Data = err
		h.pub.Publish(event)
	}
}

func (h *Handler) updateMissedMarketData(ctx context.Context, agg domain.Aggregate[Portfolio]) {
	pos := agg.Entity.Positions

	for posN := range pos {
		if pos[posN].Price != 0 {
			continue
		}

		data, err := h.data.Get(ctx, market.ID(pos[posN].Ticker))
		if err != nil {
			h.pub.Publish(
				domain.Event{
					QID:       agg.QID(),
					Timestamp: agg.Timestamp,
					Data:      err,
				},
			)
		}

		pos[posN].Price = data.Entity.Price

		if !data.Timestamp.Before(agg.Timestamp) {
			pos[posN].Turnover = data.Entity.Turnover
		}
	}
}
