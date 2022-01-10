package domain

import "time"

// Event - событие, произошедшее во время работы программы.
type Event interface {
	Version
}

// UpdateCompleted - событие удачного обновления таблицы.
type UpdateCompleted struct {
	Version
}

func NewUpdateCompleted(ver Version) UpdateCompleted {
	return UpdateCompleted{Version: ver}
}

func NewUpdateCompletedFromID(id ID, time time.Time) UpdateCompleted {
	return UpdateCompleted{Version: NewVersion(id, time)}
}

// ErrorOccurred - событие неудачного обновления таблицы.
type ErrorOccurred struct {
	Version
	Err error
}

func NewErrorOccurred(ver Version, err error) ErrorOccurred {
	return ErrorOccurred{Version: ver, Err: err}
}
