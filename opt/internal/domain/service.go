package domain

import (
	"fmt"
	"net/http"
)

// ServiceError интерфейс ошибки сервисов, обслуживающих внешнее API.
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
