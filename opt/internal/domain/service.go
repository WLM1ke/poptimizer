package domain

import (
	"fmt"
	"net/http"
	"time"
)

// DataStartDate начало статистики для внешнего использования.
//
// Хотя часть данных присутствует на более раннюю дату, некоторые данные, например, дивиденды, начинаются с указанной
// даты, поэтому для согласованности лучше обрезать предоставляемые данные по указанной дате.
func DataStartDate() time.Time {
	return time.Date(2015, time.January, 1, 0, 0, 0, 0, time.UTC)
}

// ServiceError интерфейс ошибки сервисов.
type ServiceError interface {
	error
	Write(w http.ResponseWriter)
}

// ServiceInternalErr конкретная реализация для внутренних ошибок приложения.
type ServiceInternalErr struct {
	error
}

// NewServiceInternalErr создает внутреннюю ошибку сервиса.
func NewServiceInternalErr(err error) ServiceInternalErr {
	return ServiceInternalErr{error: err}
}

func (e ServiceInternalErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusInternalServerError)
}

// BadServiceRequestErr ошибка сервиса связанная с некорректным запросом к нему.
type BadServiceRequestErr struct {
	error
}

// NewBadServiceRequestErr создает ошибку для некорректного запроса к сервису.
func NewBadServiceRequestErr(format string, args ...any) BadServiceRequestErr {
	return BadServiceRequestErr{error: fmt.Errorf(format, args...)}
}

func (e BadServiceRequestErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusBadRequest)
}
