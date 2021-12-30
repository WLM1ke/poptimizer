package events

type (
	// Group тип наименования группы таблиц.
	Group string
	// Name тип названия таблицы.
	Name string
)

// ID идентификатор таблицы.
//
// Таблицы разделены на группы с похожим типом информации и имеют имя в рамках группы. Если группа содержит одну
// таблицу, то ее имя обычно совпадает с названием группы.
type ID struct {
	group Group
	name  Name
}

// NewID создает новый id таблицы.
func NewID(group, name string) ID {
	return ID{group: Group(group), name: Name(name)}
}

// Group возвращает группу таблицы.
func (i ID) Group() Group {
	return i.group
}

// Name возвращает наименование таблицы.
func (i ID) Name() Name {
	return i.name
}
