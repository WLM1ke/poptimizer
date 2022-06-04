package domain

import (
	"bytes"
	"encoding/gob"
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

	var b bytes.Buffer
	if err := gob.NewEncoder(&b).Encode(&dao); err != nil {
		return nil, err
	}

	return b.Bytes(), nil
}

// GobDecode поддержка декодирования скрытых полей.
func (a *Aggregate[E]) GobDecode(b []byte) error {
	dao := &struct {
		ID        QualifiedID
		Ver       int
		Timestamp time.Time
		Entity    E
	}{}

	reader := bytes.NewReader(b)
	if err := gob.NewDecoder(reader).Decode(&dao); err != nil {
		return err
	}

	a.id = dao.ID
	a.ver = dao.Ver
	a.Timestamp = dao.Timestamp
	a.Entity = dao.Entity

	return nil
}
