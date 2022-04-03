package domain

import (
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02 15:04:05"

// Versioned отражает идентификатор и время последнего обновления или события.
type Versioned interface {
	ID() ID
	Date() time.Time
}

type ver struct {
	id   ID
	date time.Time
}

// Group - группа таблицы. Группа может содержать одну или несколько таблиц.
func (v ver) Group() Group {
	return v.id.group
}

// Name - наименование талицы в группе. Если в группе одна таблица, то ее название обычно совпадает с названием группы.
func (v ver) Name() Name {
	return v.id.name
}

// ID - идентификатор таблицы и связанных с ней событий.
func (v ver) ID() ID {
	return v.id
}

// Date - время последнего обновления или соответствующего события.
func (v ver) Date() time.Time {
	return v.date
}

// String - строковое представление версии.
func (v ver) String() string {
	return fmt.Sprintf(
		"%s, %s, %s",
		v.Group(),
		v.Name(),
		v.Date().In(loc).Format(_timeFormat),
	)
}
