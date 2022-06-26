package domain

import (
	"context"
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02"

// QID уникальный идентификатор сущности доменной области.
//
// Каждый доменный объект принадлежит к поддомену, группе однородных объектов и имеет уникальный ID в рамках группы.
type QID struct {
	Sub   string
	Group string
	ID    string
}

func (q QID) String() string {
	return fmt.Sprintf(
		"QID(%q, %q, %q)",
		q.Sub,
		q.Group,
		q.ID,
	)
}

// Event представляет событие, с изменением объекта.
type Event struct {
	QID
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
