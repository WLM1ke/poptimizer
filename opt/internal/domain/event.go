package domain

import (
	"context"
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02"

// QualifiedID уникальный идентификатор объекта.
type QualifiedID struct {
	BoundedCtx string
	Aggregate  string
	ID         string
}

// Event представляет событие, с изменением объекта.
type Event struct {
	QualifiedID
	Timestamp time.Time
	Data      any
}

func (e Event) String() string {
	return fmt.Sprintf(
		"Event(%s, %s, %s, %s)",
		e.BoundedCtx,
		e.Aggregate,
		e.ID,
		e.Timestamp.Format(_timeFormat),
	)
}

// Publisher - интерфейс для рассылки сообщений.
type Publisher interface {
	Publish(event Event)
}

// EventHandler обработчик события.
type EventHandler interface {
	Handler(ctx context.Context, event Event) error
}
