package domain

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[T any] struct {
	Version
	Rows []T
}
