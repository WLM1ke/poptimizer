package domain

import (
	"context"
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02"

// QualifiedID уникальный идентификатор сущности доменной области.
//
// Каждый доменный объект принадлежит к поддомену, группе однородных объектов и имеет уникальный ID в рамках группы.
type QualifiedID struct {
	Sub   string
	Group string
	ID    string
}

func (q QualifiedID) String() string {
	return fmt.Sprintf(
		"QID(%q, %q, %q)",
		q.Sub,
		q.Group,
		q.ID,
	)
}

// Event представляет событие, с изменением объекта.
type Event struct {
	QualifiedID
	Timestamp time.Time
	Data      any
}

func (e Event) String() string {
	return fmt.Sprintf(
		"Event(%q, %q, %q, %s)",
		e.Sub,
		e.Group,
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
	Match(event Event) bool
	Handle(ctx context.Context, event Event)
	fmt.Stringer
}

// Subscriber - интерфейс подписки на сообщения соответствующего топика.
type Subscriber interface {
	Subscribe(EventHandler)
}

// Bus - интерфейс шины сообщений.
type Bus interface {
	Subscriber
	Publisher
}
