package domain

type (
	// Group наименование группы таблиц.
	Group string
	// Name название таблицы.
	Name string
)

// ID - идентификатор таблицы и связанных с ней событий.
type ID struct {
	group Group
	name  Name
}

// NewID создает новый идентификатор.
func NewID(group, name string) ID {
	return ID{group: Group(group), name: Name(name)}
}

// Group - группа таблицы. Группа может содержать одну или несколько таблиц.
func (id ID) Group() Group {
	return id.group
}

// Name - наименование талицы в группе. Если в группе одна таблица, то ее название обычно совпадает с названием группы.
func (id ID) Name() Name {
	return id.name
}
