package domain

import (
	"bytes"
	"encoding/gob"
	"fmt"
	"time"
)

// Aggregate представляет доменный объект с данными, актуальными на конкретную дату.
type Aggregate[E any] struct {
	id        QualifiedID
	ver       int
	Timestamp time.Time
	Entity    E
}

// newEmptyAggregate создает пустой агрегат.
func newEmptyAggregate[E any](id QualifiedID) Aggregate[E] {
	return Aggregate[E]{
		id: id,
	}
}

// newAggregate создает агрегат, содержащий данные.
func newAggregate[E any](id QualifiedID, ver int, timestamp time.Time, data E) Aggregate[E] {
	return Aggregate[E]{
		id:        id,
		ver:       ver,
		Timestamp: timestamp,
		Entity:    data,
	}
}

// GobEncode поддержка кодирования скрытых полей.
func (a Aggregate[E]) GobEncode() ([]byte, error) {
	dao := &struct {
		ID        QualifiedID
		Ver       int
		Timestamp time.Time
		Entity    E
	}{
		ID:        a.id,
		Ver:       a.ver,
		Timestamp: a.Timestamp,
		Entity:    a.Entity,
	}

	var data bytes.Buffer
	if err := gob.NewEncoder(&data).Encode(&dao); err != nil {
		return nil, fmt.Errorf("can't encode aggregate %s -> %w", a.id, err)
	}

	return data.Bytes(), nil
}

// GobDecode поддержка декодирования скрытых полей.
func (a *Aggregate[E]) GobDecode(data []byte) error {
	dao := &struct {
		ID        QualifiedID
		Ver       int
		Timestamp time.Time
		Entity    E
	}{}

	reader := bytes.NewReader(data)
	if err := gob.NewDecoder(reader).Decode(&dao); err != nil {
		return fmt.Errorf("can't decode aggregate -> %w", err)
	}

	a.id = dao.ID
	a.ver = dao.Ver
	a.Timestamp = dao.Timestamp
	a.Entity = dao.Entity

	return nil
}
