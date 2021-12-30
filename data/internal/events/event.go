package events

// Event отражает события, связанные с таблицами.
type Event interface {
	ID() ID
}
