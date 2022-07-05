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

const (
	_timeout    = 30 * time.Second
	_bufferSize = 256
)

// Handler обработчик событий, отвечающий за обновление портфелей.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadGroupWriteRepo[Portfolio]

	lock     sync.RWMutex
	stopping bool

	work   chan domain.Event
	closed chan struct{}
}

// NewHandler создает обработчик для актуализации данных портфелей.
func NewHandler(pub domain.Publisher, repo domain.ReadGroupWriteRepo[Portfolio]) *Handler {
	handler := Handler{
		pub:    pub,
		repo:   repo,
		lock:   sync.RWMutex{},
		work:   make(chan domain.Event, _bufferSize),
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
			QID:       ID(_Group),
			Timestamp: event.Timestamp,
			Data:      fmt.Errorf("trying to handle %v with stopped handler", event),
		})

		return
	}

	select {
	case h.work <- event:
	case <-ctx.Done():
		h.pub.Publish(domain.Event{
			QID:       ID(_Group),
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

	for _, agg := range aggs {
		if err := h.repo.Save(ctx, agg); err != nil {
			h.pub.Publish(domain.Event{
				QID:       agg.QID(),
				Timestamp: agg.Timestamp,
				Data:      err,
			})
		}
	}

	h.pub.Publish(domain.Event{
		QID:       ID(_Group),
		Timestamp: time.Now(),
		Data:      fmt.Errorf("сохранение"),
	})
}

func (h *Handler) handleEvent(
	event domain.Event,
	aggs []domain.Aggregate[Portfolio],
) []domain.Aggregate[Portfolio] {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	aggs, err := h.loadAggs(ctx, aggs, event.Timestamp)
	if err != nil {
		event.QID = ID(_Group)
		event.Data = err

		h.pub.Publish(event)

		return nil
	}

	switch data := event.Data.(type) {
	case securities.Table:
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
		}
	case market.Data:
		for nAgg := range aggs {
			newDay := event.Timestamp.After(aggs[nAgg].Timestamp)
			if newDay {
				aggs[nAgg].Timestamp = event.Timestamp
			}

			ticker := event.ID
			aggs[nAgg].Entity.UpdateMarketData(ticker, data.Price, data.Turnover, newDay)
		}
	default:
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)
	}

	return aggs
}

func (h *Handler) loadAggs(
	ctx context.Context,
	aggs []domain.Aggregate[Portfolio],
	timestamp time.Time,
) ([]domain.Aggregate[Portfolio], error) {
	if aggs != nil {
		return aggs, nil
	}

	aggs, err := h.repo.GetGroup(ctx, portfolio.Subdomain, _Group)
	if err != nil {
		return nil, err
	}

	if len(aggs) > 0 {
		return aggs, nil
	}

	agg, err := h.repo.Get(ctx, ID(_NewAccount))
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
