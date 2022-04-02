package domain

import (
	"fmt"
	"time"
)
// Информация о торгах публикуется на MOEX ISS в 0:45 по московскому времени на следующий день.
const (
	_issTZ     = "Europe/Moscow"
	_issHour   = 0
	_issMinute = 45
)

var loc = func() *time.Location { //nolint:gochecknoglobals
	loc, err := time.LoadLocation(_issTZ)
	if err != nil {
		panic("can't load time zone")
	}

	return loc
}()

// LastTradingDate возвращает предполагаемую последнюю торговую дату MOEX, для которой была опубликована статистика.
func LastTradingDate() time.Time {
	now := time.Now().In(loc)
	end := time.Date(now.Year(), now.Month(), now.Day(), _issHour, _issMinute, 0, 0, loc)

	delta := 2
	if end.Before(now) {
		delta = 1
	}

	return time.Date(now.Year(), now.Month(), now.Day()-delta, 0, 0, 0, 0, time.UTC)
}

// Event - событие, произошедшее во время работы программы.
type Event interface {
	Versioned
	fmt.Stringer
}

// UpdateCompleted - событие удачного обновления таблицы.
type UpdateCompleted struct {
	ver
}

// NewUpdateCompleted создает событие об обновлении таблицы.
func NewUpdateCompleted(id ID, date time.Time) UpdateCompleted {
	return UpdateCompleted{ver: ver{id: id, date: date}}
}

func (u UpdateCompleted) String() string {
	return fmt.Sprintf(
		"UpdateCompleted(%s)",
		u.ver,
	)
}

// ErrorOccurred - событие неудачного обновления таблицы.
type ErrorOccurred struct {
	ver
	err error
}

// NewErrorOccurred создает событие об ошибке при обновлении таблицы.
func NewErrorOccurred(v Versioned, err error) ErrorOccurred {
	return ErrorOccurred{
		ver: ver{id: v.ID(), date: v.Date()},
		err: err,
	}
}

func (e ErrorOccurred) String() string {
	return fmt.Sprintf(
		"ErrorOccurred(%s, %s)",
		e.ver,
		e.err,
	)
}
