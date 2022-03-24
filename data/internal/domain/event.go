package domain

import (
	"fmt"
	"time"
)

// Event - событие, произошедшее во время работы программы.
type Event interface {
	Versioned
	fmt.Stringer
}

// UpdateCompleted - событие удачного обновления таблицы.
type UpdateCompleted struct {
	ver
}

func NewUpdateCompleted(id ID, date time.Time) UpdateCompleted {
	return UpdateCompleted{ver: ver{id: id, date: date}}
}

func (u UpdateCompleted) String() string {
	return fmt.Sprintf(
		"UpdateCompleted(%s)",
		u.ver,
	)
}

// ErrorOccurred - событие неудачного обновления таблицы.
type ErrorOccurred struct {
	ver
	err error
}

func NewErrorOccurred(v Versioned, err error) ErrorOccurred {
	return ErrorOccurred{
		ver: ver{id: v.ID(), date: v.Date()},
		err: err,
	}
}

func (e ErrorOccurred) String() string {
	return fmt.Sprintf(
		"ErrorOccurred(%s, %s)",
		e.ver,
		e.err,
	)
}
