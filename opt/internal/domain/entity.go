package domain

import "time"

// Entity представляет доменный объект с данными, актуальными на конкретную дату.
type Entity[D any] struct {
	QualifiedID
	Timestamp time.Time
	Data      D
}

// NewEmptyEntity создает пустую таблицу.
func NewEmptyEntity[D any](id QualifiedID) Entity[D] {
	return Entity[D]{
		QualifiedID: id,
	}
}

// NewTable создает заполненную таблицу.
func NewTable[D any](id QualifiedID, timestamp time.Time, data D) Entity[D] {
	return Entity[D]{
		QualifiedID: id,
		Timestamp:   timestamp,
		Data:        data,
	}
}
