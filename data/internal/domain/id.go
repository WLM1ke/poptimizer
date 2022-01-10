package domain

type (
	// Group наименование группы таблиц.
	Group string
	// Name название таблицы.
	Name string
)

type ID interface {
	Group() Group
	Name() Name
}

type id struct {
	group Group
	name  Name
}

func NewId(group Group, name Name) ID {
	return id{group: group, name: name}
}

func (id id) Group() Group {
	return id.group
}

func (id id) Name() Name {
	return id.name
}

func CompareID(id1, id2 ID) bool {
	return (id1.Group() == id2.Group()) && (id1.Name() == id2.Name())
}
