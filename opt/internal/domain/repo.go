package domain

import (
	"context"
	"errors"
)

// ErrWrongVersion ошибка попытки записи неверной версии агрегата в рамках optimistic concurrency control.
var ErrWrongVersion = errors.New("wrong agg version")

// ReadRepo осуществляет загрузку объекта.
type ReadRepo[E Entity] interface {
	// Get загружает объект.
	Get(ctx context.Context, qid QualifiedID) (Aggregate[E], error)
}

// ReadWriteRepo осуществляет загрузку и сохранение объекта.
type ReadWriteRepo[E Entity] interface {
	ReadRepo[E]
	// Save перезаписывает объект.
	Save(ctx context.Context, agg Aggregate[E]) error
}

// ReadAppendRepo осуществляет загрузку и дополнение данных объекта.
type ReadAppendRepo[E Entity] interface {
	ReadRepo[E]
	// Append добавляет данные в конец слайса с данными.
	Append(ctx context.Context, agg Aggregate[E]) error
}
