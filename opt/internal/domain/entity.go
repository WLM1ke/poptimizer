package domain

import "time"

// Entity представляет доменный объект с данными, актуальными на конкретную дату.
type Entity[D any] struct {
	id        QualifiedID
	ver       int
	Timestamp time.Time
	Data      D
}

// newEmptyEntity создает пустую таблицу.
func newEmptyEntity[D any](id QualifiedID) Entity[D] {
	return Entity[D]{
		id: id,
	}
}

// newEntity создает заполненную таблицу.
func newEntity[D any](id QualifiedID, ver int, timestamp time.Time, data D) Entity[D] {
	return Entity[D]{
		id:        id,
		ver:       ver,
		Timestamp: timestamp,
		Data:      data,
	}
}
