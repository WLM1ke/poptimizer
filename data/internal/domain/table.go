package domain

import "time"

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[R any] struct {
	ver
	rows []R
}

func NewEmptyTable[R any](id ID) Table[R] {
	return Table[R]{
		ver: ver{id: id},
	}
}

func NewTable[R any](id ID, date time.Time, rows []R) Table[R] {
	return Table[R]{
		ver:  ver{id: id, date: date},
		rows: rows,
	}
}

func (t Table[R]) Rows() []R {
	return t.rows
}

func (t Table[R]) IsEmpty() bool {
	return len(t.rows) == 0
}

func (t Table[R]) LastRow() R {
	return t.rows[len(t.rows)-1]
}
