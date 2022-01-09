package domain

// Table представляет таблицу с данными, актуальными на конкретную дату.
type Table[T comparable] struct {
	Version
	Rows []T
}
