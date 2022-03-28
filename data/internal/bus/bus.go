// Package bus содержит реализацию шины обработки событий.
package bus

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/rules/cpi"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dividends"
	"github.com/WLM1ke/poptimizer/data/internal/rules/indexes"
	"github.com/WLM1ke/poptimizer/data/internal/rules/quotes"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
	"github.com/WLM1ke/poptimizer/data/internal/rules/status"

	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"go.mongodb.org/mongo-driver/mongo"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/end"
	"github.com/WLM1ke/poptimizer/data/internal/rules/errors"
	"github.com/WLM1ke/poptimizer/data/pkg/channels"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const _timeout = 3 * time.Minute

// errUnprocessedEvent ошибка связанная с наличием необработанных ошибок в момент завершения работы шины событий.
var errUnprocessedEvent = fmt.Errorf("unprocessed event")

// EventBus осуществляет перенаправление исходящих событий правилам по их обработке.
type EventBus struct {
	logger *lgr.Logger
	rules  []domain.Rule
}

// NewEventBus создает шину событий со всеми правилами обработки событий.
func NewEventBus(
	logger *lgr.Logger,
	db *mongo.Database,
	client *http.Client,
	telegram *client.Telegram,
) *EventBus {
	iss := gomoex.NewISSClient(client)

	rules := []domain.Rule{
		errors.New(logger, telegram, _timeout),
		end.New(logger, _timeout),
		dates.New(logger, db, iss, _timeout),
		usd.New(logger, db, iss, _timeout),
		cpi.New(logger, db, client, _timeout),
		securities.New(logger, db, iss, _timeout),
		status.New(logger, db, client, _timeout),
		indexes.New(logger, db, iss, _timeout),
		quotes.New(logger, db, iss, _timeout),
		dividends.New(logger, db, _timeout),
		raw_div.New(logger, db, _timeout),
	}

	return &EventBus{
		logger: logger,
		rules:  rules,
	}
}

// Run запускает шину событий.
func (b *EventBus) Run(ctx context.Context) error {
	broadcast := make(chan domain.Event)
	inbox := b.activateConsumers(broadcast)

	b.formInboxToBroadcast(ctx, inbox, broadcast)

	if count := b.drainUnprocessedEvents(inbox); count != 0 {
		return fmt.Errorf("%w: count %d", errUnprocessedEvent, count)
	}

	return nil
}

func (b *EventBus) activateConsumers(broadcast <-chan domain.Event) <-chan domain.Event {
	in := channels.FanOut(broadcast, len(b.rules))
	out := make([]<-chan domain.Event, 0, len(b.rules))

	for n, rule := range b.rules {
		out = append(out, rule.Activate(in[n]))
	}

	return channels.FanIn(out...)
}

func (b *EventBus) formInboxToBroadcast(ctx context.Context, inbox <-chan domain.Event, broadcast chan<- domain.Event) {
	for {
		select {
		case <-ctx.Done():
			close(broadcast)

			return
		case event := <-inbox:
			b.logger.Infof("EventBus: processing event %s", event)
			broadcast <- event
		}
	}
}

func (b *EventBus) drainUnprocessedEvents(inbox <-chan domain.Event) (count int) {
	for event := range inbox {
		b.logger.Warnf("EventBus: unprocessed event %s", event)
		count++
	}

	return count
}
