package events

// Err - событие ошибки при обновлении таблицы.
//
// Содержит ее id и ошибку.
type Err struct {
	id  ID
	err error
}

// NewErr создает новое событие ошибки.
func NewErr(id ID, err error) *Err {
	return &Err{id: id, err: err}
}

// ID таблицы, при обновлении которой произошла ошибка.
func (e Err) ID() ID {
	return e.id
}

// Error ошибка, которая произошла при обновлении таблицы.
func (e Err) Error() error {
	return e.err
}
