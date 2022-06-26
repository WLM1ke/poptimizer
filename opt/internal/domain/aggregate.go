package domain

import (
	"time"
)

// Entity представляет собой доменную сущность.
type Entity any

// Aggregate представляет доменный объект с данными, актуальными на конкретную дату.
type Aggregate[E Entity] struct {
	id        QID
	ver       int
	Timestamp time.Time
	Entity    E
}

func (a Aggregate[E]) QID() QID {
	return a.id
}

// newEmptyAggregate создает пустой агрегат.
func newEmptyAggregate[E Entity](id QID) Aggregate[E] {
	return Aggregate[E]{
		id: id,
	}
}

// newAggregate создает агрегат, содержащий данные.
func newAggregate[E Entity](id QID, ver int, timestamp time.Time, data E) Aggregate[E] {
	return Aggregate[E]{
		id:        id,
		ver:       ver,
		Timestamp: timestamp,
		Entity:    data,
	}
}
