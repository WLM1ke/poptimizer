package domain

import "time"

type (
	// Group наименование группы таблиц.
	Group string
	// Name название таблицы.
	Name string
)

// ID уникальный идентификатор таблицы.
type ID struct {
	Group Group
	Name  Name
}

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[T comparable] struct {
	ID
	Date time.Time
	Rows []T
}
