package bus

import (
	"context"
	"fmt"
	"sync"

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
func NewEventBus(logger *lgr.Logger) *EventBus {
	rules := []domain.Rule{}

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
		consumer := make(chan domain.Event)
		b.consumers = append(b.consumers, consumer)

		b.wg.Add(1)

		go func(rule domain.Rule) {
			defer b.wg.Done()

			rule.Activate(consumer, b.inbox)
		}(rule)
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
			b.logger.Infof("EventBus: %v", event)
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
		b.logger.Warnf("EventBus: unprocessed %v", event)
		count++
	}

	return count
}
