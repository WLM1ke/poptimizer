package domain

import (
	"fmt"
	"time"
)

// QID уникальный идентификатор сущности доменной области.
//
// Каждый доменный объект принадлежит к поддомену, группе однородных объектов и имеет уникальный ID в рамках группы.
type QID struct {
	Sub   string
	Group string
	ID    string
}

func (q QID) String() string {
	return fmt.Sprintf(
		"QID(%q, %q, %q)",
		q.Sub,
		q.Group,
		q.ID,
	)
}

// Entity представляет собой доменную сущность.
type Entity any

// Aggregate представляет доменный объект с данными, актуальными на конкретную дату.
type Aggregate[E Entity] interface {
	QID() QID
	Ver() int
	Timestamp() time.Time
	Entity() E
	Update(entity E, timestamp time.Time)
	UpdateSameDate(entity E)
}

// DataStartDate начало статистики для внешнего использования.
//
// Хотя часть данных присутствует на более раннюю дату, некоторые данные, например, дивиденды, начинаются с указанной
// даты, поэтому для согласованности лучше обрезать предоставляемые данные по указанной дате.
func DataStartDate() time.Time {
	return time.Date(2015, time.January, 1, 0, 0, 0, 0, time.UTC)
}
