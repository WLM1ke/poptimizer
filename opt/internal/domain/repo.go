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

// ListRepo выводит перечень id агрегатов в заданной группе.
type ListRepo interface {
	List(ctx context.Context, sub, group string) ([]string, error)
}

// ReadGroupRepo осуществляет загрузку всех объектов группы.
type ReadGroupRepo[E Entity] interface {
	GetGroup(ctx context.Context, sub, group string) ([]Aggregate[E], error)
}

// WriteRepo осуществляет сохранение объекта.
type WriteRepo[E Entity] interface {
	Save(ctx context.Context, agg Aggregate[E]) error
}

// DeleteRepo осуществляет сохранение объекта.
type DeleteRepo interface {
	Delete(ctx context.Context, qid QID) error
}

// JSONViewer загружает ExtendedJSON представление сущности.
type JSONViewer interface {
	GetJSON(ctx context.Context, qid QID) ([]byte, error)
}

// GetListRepo осуществляет просмотр перечня объектов в группе и их загрузку.
type GetListRepo[E Entity] interface {
	ReadRepo[E]
	ListRepo
}

// ReadWriteRepo осуществляет загрузку и сохранение объекта.
type ReadWriteRepo[E Entity] interface {
	ReadRepo[E]
	WriteRepo[E]
}

// ReadAppendRepo осуществляет загрузку и дополнение данных объекта.
type ReadAppendRepo[E Entity] interface {
	ReadRepo[E]
	// Append добавляет данные в конец слайса с данными.
	Append(ctx context.Context, agg Aggregate[E]) error
}

// ReadGroupWriteRepo осуществляет загрузку всех объектов группы и сохранение отдельных объектов.
type ReadGroupWriteRepo[E Entity] interface {
	ReadRepo[E]
	ReadGroupRepo[E]
	WriteRepo[E]
}

// FullRepo осуществляет загрузку всех объектов группы, сохранение и удаление отдельных объектов.
type FullRepo[E Entity] interface {
	ReadRepo[E]
	ListRepo
	ReadGroupRepo[E]
	WriteRepo[E]
	DeleteRepo
}
