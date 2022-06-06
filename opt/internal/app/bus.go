package app

import (
	"context"
	"fmt"
	"go.mongodb.org/mongo-driver/mongo"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const (
	_eventTimeout = time.Minute * 5
	_errorTimeout = time.Second * 30
)

// EventBus - шина событий. Позволяет публиковать их и подписываться на заданный топик.
type EventBus struct {
	logger *lgr.Logger

	handlers []domain.EventHandler
	inbox    chan domain.Event

	lock    sync.RWMutex
	stopped bool
}

// PrepareEventBus создает шину сообщений и настраивает все обработчики.
func PrepareEventBus(
	ctx context.Context,
	logger *lgr.Logger,
	uri string,
	telegram *clients.Telegram,
	iss *gomoex.ISSClient,
) (*mongo.Client, *EventBus) {
	client := prepareDB(ctx, logger, uri)

	logger = logger.WithPrefix("EventBus")
	bus := EventBus{
		logger: logger,
		inbox:  make(chan domain.Event),
	}

	bus.Subscribe(NewErrorsHandler(logger, telegram))
	bus.Subscribe(NewBackupHandler(logger, &bus, uri))

	bus.Subscribe(data.NewUSDHandler(&bus, domain.NewRepo[data.Rows[data.USD]](client), iss))
	bus.Subscribe(data.NewSecuritiesHandler(&bus, domain.NewRepo[data.Rows[data.Security]](client), iss))

	bus.Subscribe(selected.NewHandler(&bus, domain.NewRepo[selected.Tickers](client)))

	return client, &bus
}

// Subscribe регистрирует обработчик для событий заданного топика.
func (e *EventBus) Subscribe(handler domain.EventHandler) {
	e.logger.Infof("registered %s", handler)

	e.handlers = append(e.handlers, handler)
}

// Run запускает шину.
//
// Запуск допускается один раз. События обрабатываются конкурентно.
func (e *EventBus) Run(ctx context.Context) error {
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

			return nil
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
	e.logger.Infof("handling %s", event)

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, h := range e.handlers {
		if h.Match(event) {
			handler := h

			waitGroup.Add(1)

			go func() {
				defer waitGroup.Done()

				ctx, cancel := context.WithTimeout(context.Background(), _eventTimeout)
				defer cancel()

				handler.Handle(ctx, event)
			}()
		}
	}
}

// Publish публикует событие в шину сообщений для рассылки подписчикам.
func (e *EventBus) Publish(event domain.Event) {
	e.lock.RLock()
	defer e.lock.RUnlock()

	if e.stopped {
		err := fmt.Errorf("stopped before handling event %s", event)
		e.logger.Warnf("can't handle event -> %s", err)

		return
	}

	e.inbox <- event
}
