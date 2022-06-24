package domain

import (
	"time"
)

// Entity представляет собой доменную сущность.
type Entity any

// Aggregate представляет доменный объект с данными, актуальными на конкретную дату.
type Aggregate[E Entity] struct {
	id        QualifiedID
	ver       int
	Timestamp time.Time
	Entity    E
}

// newEmptyAggregate создает пустой агрегат.
func newEmptyAggregate[E Entity](id QualifiedID) Aggregate[E] {
	return Aggregate[E]{
		id: id,
	}
}

// newAggregate создает агрегат, содержащий данные.
func newAggregate[E Entity](id QualifiedID, ver int, timestamp time.Time, data E) Aggregate[E] {
	return Aggregate[E]{
		id:        id,
		ver:       ver,
		Timestamp: timestamp,
		Entity:    data,
	}
}
