package repository

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

type aggregate[E domain.Entity] struct {
	qid       domain.QID
	ver       int
	timestamp time.Time
	entity    E
}

func newEmptyAggregate[E domain.Entity](qid domain.QID) *aggregate[E] {
	return &aggregate[E]{qid: qid}
}

type aggDAO[E domain.Entity] struct {
	ID        string    `bson:"_id"`
	Ver       int       `bson:"ver"`
	Timestamp time.Time `bson:"timestamp"`
	Data      E         `bson:"data"`
}

func newAggregate[E domain.Entity](qid domain.QID, dao aggDAO[E]) *aggregate[E] {
	return &aggregate[E]{
		qid:       qid,
		ver:       dao.Ver,
		timestamp: dao.Timestamp,
		entity:    dao.Data,
	}
}

func (a aggregate[E]) QID() domain.QID {
	return a.qid
}

func (a aggregate[E]) Ver() int {
	return a.ver
}

func (a aggregate[E]) Timestamp() time.Time {
	return a.timestamp
}

func (a aggregate[E]) Entity() E {
	return a.entity
}

func (a *aggregate[E]) Update(entity E, timestamp time.Time) {
	a.entity = entity
	a.timestamp = timestamp
}

func (a *aggregate[E]) UpdateSameDate(entity E) {
	a.entity = entity
}
