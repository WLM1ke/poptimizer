package domain

import (
	"fmt"
	"net/http"
)

type ServiceError interface {
	error
	Write(w http.ResponseWriter)
}

type ServiceInternalErr struct {
	error
}

func NewServiceInternalErr(error error) ServiceInternalErr {
	return ServiceInternalErr{error: error}
}

func (e ServiceInternalErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusInternalServerError)
}

type BadServiceRequestErr struct {
	error
}

func NewBadServiceRequestErr(format string, args ...any) BadServiceRequestErr {
	return BadServiceRequestErr{error: fmt.Errorf(format, args...)}
}

func (e BadServiceRequestErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusBadRequest)
}
