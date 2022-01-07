package domain

import "time"

// Event - событие, произошедшее во время работы программы.
type Event interface{}

// TableUpdated - событие удачного обновления таблицы.
type TableUpdated struct {
	ID
	Date time.Time
}

// UpdatedErrHappened - событие неудачного обновления таблицы.
type UpdatedErrHappened struct {
	ID
	Date time.Time
	Err  error
}
