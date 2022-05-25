package bus

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_eventTimeout = time.Minute * 5
	_errorTimeout = time.Second * 30
)

// Filter для выбора сообщений.
//
// Если соответсвующее поле не заполнено, то подходит событие с любым значением соответствующего поля.
type Filter struct {
	BoundedCtx string
	Aggregate  string
	ID         string
}

// Match проверяет соответствие события фильтру.
func (s Filter) Match(event domain.Event) bool {
	switch {
	case s.ID != "" && event.ID != s.ID:
		return false
	case s.Aggregate != "" && event.Aggregate != s.Aggregate:
		return false
	case s.BoundedCtx != "" && event.BoundedCtx != s.BoundedCtx:
		return false
	}

	return true
}

// Subscriber - интерфейс подписки на сообщения соответствующего топика.
type Subscriber interface {
	Subscribe(filter Filter, handler domain.EventHandler)
}

type subscription struct {
	filter  Filter
	handler domain.EventHandler
}

// EventBus - шина событий. Позволяет публиковать их и подписываться на заданный топик.
type EventBus struct {
	logger   *lgr.Logger
	telegram *clients.Telegram

	subscriptions []subscription
	inbox         chan domain.Event

	lock    sync.RWMutex
	stopped bool
}

// NewEventBus создает шину сообщений.
func NewEventBus(logger *lgr.Logger, telegram *clients.Telegram) *EventBus {
	return &EventBus{
		logger:   logger,
		telegram: telegram,
		inbox:    make(chan domain.Event),
	}
}

// Subscribe регистрирует обработчик для событий заданного топика.
func (e *EventBus) Subscribe(filter Filter, handler domain.EventHandler) {
	e.subscriptions = append(e.subscriptions, subscription{
		filter:  filter,
		handler: handler,
	})
}

// Run запускает шину.
//
// Запуск допускается один раз. События обрабатываются конкурентно.
func (e *EventBus) Run(ctx context.Context) {
	e.logger.Infof("started")
	defer e.logger.Infof("stopped")

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for {
		select {
		case event := <-e.inbox:
			waitGroup.Add(1)

			go func() {
				defer waitGroup.Done()

				e.handle(event)
			}()
		case <-ctx.Done():
			e.stop()

			return
		}
	}
}

func (e *EventBus) stop() {
	e.lock.Lock()
	defer e.lock.Unlock()

	e.stopped = true
	close(e.inbox)
}

func (e *EventBus) handle(event domain.Event) {
	e.logger.Infof("handling event -> %s", event)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, sub := range e.subscriptions {
		if sub.filter.Match(event) {
			handler := sub.handler

			waitGroup.Add(1)

			go func() {
				defer waitGroup.Done()

				ctx, cancel := context.WithTimeout(context.Background(), _eventTimeout)
				defer cancel()

				e.logErr(handler.Handler(ctx, event))
			}()
		}
	}
}

// Publish публикует событие в шину сообщений для рассылки подписчикам.
func (e *EventBus) Publish(event domain.Event) {
	e.lock.RLock()
	defer e.lock.RUnlock()

	if e.stopped {
		e.logErr(fmt.Errorf("stopped before handling event %s", event))

		return
	}

	e.inbox <- event
}

func (e *EventBus) logErr(err error) {
	if err == nil {
		return
	}

	e.logger.Warnf("can't handle event -> %s", err)

	ctx, cancel := context.WithTimeout(context.Background(), _errorTimeout)
	defer cancel()

	if err = e.telegram.Send(ctx, err.Error()); err != nil {
		e.logger.Warnf("can't send notification -> %s", err)
	}
}
