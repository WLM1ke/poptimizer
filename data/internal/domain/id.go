package domain

type (
	// Group наименование группы таблиц.
	Group string
	// Name название таблицы.
	Name string
)

type ID struct {
	group Group
	name  Name
}

func NewID(group, name string) ID {
	return ID{group: Group(group), name: Name(name)}
}

func (id ID) Group() Group {
	return id.group
}

func (id ID) Name() Name {
	return id.name
}
