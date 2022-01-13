package domain

import "time"

type Version struct {
	ID
	Date time.Time
}

func (v Version) Ver() Version {
	return v
}
