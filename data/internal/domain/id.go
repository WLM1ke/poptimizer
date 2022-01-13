package domain

type (
	// Group наименование группы таблиц.
	Group string
	// Name название таблицы.
	Name string
)

type ID struct {
	Group Group
	Name  Name
}
