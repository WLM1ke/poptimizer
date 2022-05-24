package bus

import (
	"context"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// Publisher - интерфейс для рассылки сообщений.
type Publisher interface {
	Publish(event domain.Event)
}

// Subject - топик для подписки на сообщение.
type Subject struct {
	BoundedCtx string
	Aggregate  string
	ID         string
}

// Match проверяет соответствие события топику.
//
// Если соответсвующее поле подписки не заполнено, то подходит событие с любым значением поля.
func (s Subject) Match(event domain.Event) bool {
	switch {
	case s.BoundedCtx != "" && event.BoundedCtx != s.BoundedCtx:
		return false
	case s.Aggregate != "" && event.Aggregate != s.Aggregate:
		return false
	case s.ID != "" && event.ID != s.ID:
		return false
	}

	return true
}

// EventHandler обработчик события.
type EventHandler interface {
	Handler(ctx context.Context, event domain.Event) error
}

// Subscriber - интерфейс подписки на сообщения соответствующего топика.
type Subscriber interface {
	Subscribe(subj Subject, handler EventHandler)
}
