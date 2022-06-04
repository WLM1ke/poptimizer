package data

// Subdomain загрузки данных.
const Subdomain = `data`

// Rows строчки данных с MOEX ISS.
type Rows[R any] []R

// IsEmpty проверяет есть ли строки.
func (t Rows[R]) IsEmpty() bool {
	return len(t) == 0
}

// LastRow возвращает последнюю строку. Предварительно необходимо убедиться, что строки не пустые.
func (t Rows[R]) LastRow() R {
	return t[len(t)-1]
}
