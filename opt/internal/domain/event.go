package domain

import "time"

// Event представляет событие.
type Event struct {
	Timestamp time.Time

	BoundedCtx string
	Aggregate  string
	ID         string

	Data any
}
