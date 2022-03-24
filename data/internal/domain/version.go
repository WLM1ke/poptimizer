package domain

import (
	"fmt"
	"time"
)

const _timeFormat = "2006-01-02"

type Versioned interface {
	ID() ID
	Date() time.Time
}

type ver struct {
	id   ID
	date time.Time
}

func (v ver) Group() Group {
	return v.id.group
}

func (v ver) Name() Name {
	return v.id.name
}

func (v ver) ID() ID {
	return v.id
}

func (v ver) Date() time.Time {
	return v.date
}

func (v ver) String() string {
	return fmt.Sprintf(
		"%s, %s, %s",
		v.Group(),
		v.Name(),
		v.Date().UTC().Format(_timeFormat),
	)
}
