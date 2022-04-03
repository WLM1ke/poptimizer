package domain

import "time"

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[R Row] struct {
	ver
	rows []R
}

// NewEmptyTable создает пустую таблицу.
func NewEmptyTable[R Row](id ID) Table[R] {
	return Table[R]{
		ver: ver{id: id},
	}
}

// NewTable создает заполненную таблицу.
func NewTable[R Row](id ID, date time.Time, rows []R) Table[R] {
	return Table[R]{
		ver:  ver{id: id, date: date},
		rows: rows,
	}
}

// Rows возвращает строки таблицы.
func (t Table[R]) Rows() []R {
	return t.rows
}

// IsEmpty проверяет есть ли строки в таблице.
func (t Table[R]) IsEmpty() bool {
	return len(t.rows) == 0
}

// LastRow возвращает последнюю строку таблицы. Предварительно необходимо убедиться, что таблица не пустая.
func (t Table[R]) LastRow() R {
	return t.rows[len(t.rows)-1]
}
