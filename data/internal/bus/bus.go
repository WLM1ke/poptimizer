// Package bus содержит реализацию шины обработки событий.
package bus

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/rules/backup"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/cpi"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dividends"
	"github.com/WLM1ke/poptimizer/data/internal/rules/end"
	"github.com/WLM1ke/poptimizer/data/internal/rules/errors"
	"github.com/WLM1ke/poptimizer/data/internal/rules/indexes"
	"github.com/WLM1ke/poptimizer/data/internal/rules/quotes"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
	"github.com/WLM1ke/poptimizer/data/internal/rules/status"
	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"
	"github.com/WLM1ke/poptimizer/data/pkg/channels"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

const _timeout = 3 * time.Minute

var (
	errBusStopped       = fmt.Errorf("bus stopped")
	errUnprocessedEvent = fmt.Errorf("unprocessed event")
)

// EventBus осуществляет перенаправление исходящих событий правилам по их обработке.
type EventBus struct {
	logger *lgr.Logger
	rules  []domain.Rule

	broadcast chan domain.Event

	lock    sync.RWMutex
	stopped bool
}

// NewEventBus создает шину событий со всеми правилами обработки событий.
func NewEventBus(
	logger *lgr.Logger,
	dataBase *mongo.Database,
	cmd backup.Cmd,
	client *http.Client,
	telegram *client.Telegram,
) *EventBus {
	iss := gomoex.NewISSClient(client)

	rules := []domain.Rule{
		errors.New(logger, telegram, _timeout),
		end.New(logger, _timeout),
		dates.New(logger, dataBase, iss, _timeout),
		usd.New(logger, dataBase, iss, _timeout),
		cpi.New(logger, dataBase, client, _timeout),
		securities.New(logger, dataBase, iss, _timeout),
		status.New(logger, dataBase, client, _timeout),
		indexes.New(logger, dataBase, iss, _timeout),
		quotes.New(logger, dataBase, iss, _timeout),
		dividends.New(logger, dataBase, _timeout),
		raw_div.New(logger, dataBase, _timeout),
		backup.New(logger, cmd, _timeout),
	}

	return &EventBus{
		logger:    logger,
		rules:     rules,
		broadcast: make(chan domain.Event),
	}
}

// Run запускает шину событий.
func (b *EventBus) Run(ctx context.Context) error {
	inbox := b.activateConsumers()
	b.formInboxToBroadcast(ctx, inbox)

	if count := b.drainUnprocessedEvents(inbox); count != 0 {
		return fmt.Errorf("%w: count %d", errUnprocessedEvent, count)
	}

	return nil
}

func (b *EventBus) activateConsumers() <-chan domain.Event {
	in := channels.FanOut(b.broadcast, len(b.rules))
	out := make([]<-chan domain.Event, 0, len(b.rules))

	for n, rule := range b.rules {
		out = append(out, rule.Activate(in[n]))
	}

	return channels.FanIn(out...)
}

func (b *EventBus) formInboxToBroadcast(ctx context.Context, inbox <-chan domain.Event) {
	for {
		select {
		case <-ctx.Done():
			b.prepareStop()

			return
		case event := <-inbox:
			b.broadcastEvent(event)
		}
	}
}

func (b *EventBus) prepareStop() {
	b.lock.Lock()
	defer b.lock.Unlock()

	b.stopped = true
	close(b.broadcast)
}

func (b *EventBus) broadcastEvent(event domain.Event) {
	b.logger.Infof("EventBus: processing event %s", event)
	b.broadcast <- event
}

func (b *EventBus) drainUnprocessedEvents(inbox <-chan domain.Event) (count int) {
	for event := range inbox {
		b.logger.Warnf("EventBus: unprocessed event %s", event)
		count++
	}

	return count
}

// Send рассылает сообщение для последующей обработки бизнес-правилами.
func (b *EventBus) Send(event domain.Event) error {
	b.lock.RLock()
	defer b.lock.RUnlock()

	if b.stopped {
		return errBusStopped
	}

	b.broadcastEvent(event)

	return nil
}
