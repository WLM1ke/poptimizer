package domain

// Event - событие, произошедшее во время работы программы.
type Event interface {
	Version
}

// TableUpdated - событие удачного обновления таблицы.
type TableUpdated struct {
	Version
}

func NewTableUpdated(ver Version) TableUpdated {
	return TableUpdated{Version: ver}
}

// UpdatedErrHappened - событие неудачного обновления таблицы.
type UpdatedErrHappened struct {
	Version
	Err error
}

func NewUpdatedErrHappened(ver Version, err error) UpdatedErrHappened {
	return UpdatedErrHappened{Version: ver, Err: err}
}
