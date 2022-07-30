package mocks

import (
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

type aggregate[E domain.Entity] struct {
	qid       domain.QID
	timestamp time.Time
	entity    E
}

func NewEmptyAgg[E domain.Entity](qid domain.QID) *aggregate[E] {
	return &aggregate[E]{qid: qid}
}

func NewAgg[E domain.Entity](qid domain.QID, timestamp time.Time, entity E) *aggregate[E] {
	return &aggregate[E]{
		qid:       qid,
		timestamp: timestamp,
		entity:    entity,
	}
}

func (a aggregate[E]) QID() domain.QID {
	return a.qid
}

func (a aggregate[E]) Ver() int {
	return 1
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
