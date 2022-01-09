package domain

import "time"

type Version interface {
	ID
	Date() time.Time
}

type version struct {
	ID
	date time.Time
}

func NewVersion(ID ID, date time.Time) Version {
	return version{ID: ID, date: date}
}

func (v version) Date() time.Time {
	return v.date
}

func (v version) WithNewDate(date time.Time) Version {
	v.date = date

	return v
}
