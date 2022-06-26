package domain

import (
	"context"
	"errors"
)

// ErrWrongVersion ошибка попытки записи неверной версии агрегата в рамках optimistic concurrency control.
var ErrWrongVersion = errors.New("wrong agg version")

// ReadRepo осуществляет загрузку объекта.
type ReadRepo[E Entity] interface {
	Get(ctx context.Context, qid QID) (Aggregate[E], error)
}

// ReadGroupRepo осуществляет загрузку всех объектов группы.
type ReadGroupRepo[E Entity] interface {
	GetGroup(ctx context.Context, sub, group string) ([]Aggregate[E], error)
}

// WriteRepo осуществляет сохранение объекта.
type WriteRepo[E Entity] interface {
	Save(ctx context.Context, agg Aggregate[E]) error
}

// ReadWriteRepo осуществляет загрузку и сохранение объекта.
type ReadWriteRepo[E Entity] interface {
	ReadRepo[E]
	WriteRepo[E]
}

// ReadGroupWriteRepo осуществляет загрузку всех объектов группы и сохранение отдельных объектов.
type ReadGroupWriteRepo[E Entity] interface {
	ReadRepo[E]
	ReadGroupRepo[E]
	WriteRepo[E]
}

// ReadAppendRepo осуществляет загрузку и дополнение данных объекта.
type ReadAppendRepo[E Entity] interface {
	ReadRepo[E]
	// Append добавляет данные в конец слайса с данными.
	Append(ctx context.Context, agg Aggregate[E]) error
}
