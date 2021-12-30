package errors

import "github.com/WLM1ke/poptimizer/data/internal/rules/events"

// Err - событие-ошибка при обновлении таблицы.
//
// Содержит ее id и ошибку.
type Err struct {
	id  events.ID
	err error
}

// NewErr создает новое событие ошибки.
func NewErr(id events.ID, err error) *Err {
	return &Err{id: id, err: err}
}

// ID таблицы, при обновлении которой произошла ошибка.
func (e Err) ID() events.ID {
	return e.id
}

// Error ошибка, которая произошла при обновлении таблицы.
func (e Err) Error() error {
	return e.err
}
