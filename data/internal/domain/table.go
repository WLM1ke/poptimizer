package domain

import "time"

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[R any] struct {
	Version
	Rows []R
}

func NewTable[R any](id ID) Table[R] {
	return Table[R]{Version: NewVersion(id, time.Time{})}
}
