package data

// Subdomain загрузки данных.
const Subdomain = `data`

// Table таблица данных с MOEX ISS.
type Table[R any] []R

// IsEmpty проверяет есть ли строки.
func (t Table[R]) IsEmpty() bool {
	return len(t) == 0
}

// LastRow возвращает последнюю строку. Предварительно необходимо убедиться, что строки не пустые.
func (t Table[R]) LastRow() R {
	return t[len(t)-1]
}
