// Package bus содержит реализацию шины обработки событий.
package bus

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/rules/cpi"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"github.com/WLM1ke/poptimizer/data/internal/rules/end"
	"github.com/WLM1ke/poptimizer/data/internal/rules/errors"
	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"go.mongodb.org/mongo-driver/mongo"
	"net/http"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

// errUnprocessedEvent ошибка связанная с наличием необработанных ошибок в момент завершения работы шины событий.
var errUnprocessedEvent = fmt.Errorf("unprocessed event")

// EventBus осуществляет перенаправление исходящих событий правилам по их обработке.
type EventBus struct {
	logger *lgr.Logger
	rules  []domain.Rule

	// inbox канал в который правила записывают новые события
	inbox chan domain.Event
	// broadcast канал в который направляются события из inbox для рассылки в каналы отдельных правил
	broadcast chan domain.Event
	// consumers входные каналы правил, в которые дублируются события из broadcast
	consumers []chan domain.Event

	wg sync.WaitGroup
}

// NewEventBus создает шину событий со всеми правилами обработки событий.
func NewEventBus(
	logger *lgr.Logger,
	db *mongo.Database,
	client *http.Client,
	telegram *client.Telegram,
	timeout time.Duration,
) *EventBus {
	iss := gomoex.NewISSClient(client)

	rules := []domain.Rule{
		errors.New(logger, telegram, timeout),
		end.New(logger),
		dates.New(logger, db, iss, timeout),
		usd.New(logger, db, iss, timeout),
		cpi.New(logger, db, client, timeout),
	}

	return &EventBus{
		logger:    logger,
		rules:     rules,
		inbox:     make(chan domain.Event),
		broadcast: make(chan domain.Event),
	}
}

// Run запускает шину событий.
func (b *EventBus) Run(ctx context.Context) error {
	b.activateConsumers()

	b.wg.Add(1)

	go func() {
		defer b.wg.Done()

		b.broadcastToConsumers()
	}()

	b.formInboxToBroadcast(ctx)

	if count := b.drainUnprocessedEvents(b.inbox); count != 0 {
		return fmt.Errorf("%w: count %d", errUnprocessedEvent, count)
	}

	return nil
}

func (b *EventBus) activateConsumers() {
	for _, rule := range b.rules {
		rule := rule
		consumer := make(chan domain.Event)
		b.consumers = append(b.consumers, consumer)

		b.wg.Add(1)

		go func() {
			defer b.wg.Done()

			rule.Activate(consumer, b.inbox)
		}()
	}
}

func (b *EventBus) broadcastToConsumers() {
	for event := range b.broadcast {
		for _, consumer := range b.consumers {
			consumer <- event
		}
	}

	for _, consumer := range b.consumers {
		close(consumer)
	}
}

func (b *EventBus) formInboxToBroadcast(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			close(b.broadcast)

			return
		case event := <-b.inbox:
			b.logger.Infof("EventBus: processing %s", event)
			b.broadcast <- event
		}
	}
}

func (b *EventBus) drainUnprocessedEvents(inbox <-chan domain.Event) (count int) {
	go func() {
		b.wg.Wait()
		close(b.inbox)
	}()

	for event := range inbox {
		b.logger.Warnf(
			"EventBus: unprocessed %s", event)
		count++
	}

	return count
}
