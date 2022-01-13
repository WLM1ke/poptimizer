package domain

import "fmt"

const _timeFormat = "2006-01-02 15:04:05.000 MST"

// Event - событие, произошедшее во время работы программы.
type Event interface {
	Ver() Version
	fmt.Stringer
}

// UpdateCompleted - событие удачного обновления таблицы.
type UpdateCompleted struct {
	Version
}

func (u UpdateCompleted) String() string {
	return fmt.Sprintf(
		"%T(%s, %s, %s)",
		u,
		u.Group,
		u.Name,
		u.Date.UTC().Format(_timeFormat),
	)
}

// ErrorOccurred - событие неудачного обновления таблицы.
type ErrorOccurred struct {
	Version
	Err error
}

func (e ErrorOccurred) String() string {
	return fmt.Sprintf(
		"%T(%s, %s, %s, %s)",
		e,
		e.Group,
		e.Name,
		e.Date.UTC().Format(_timeFormat),
		e.Err,
	)
}
