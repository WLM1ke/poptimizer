package domain

import (
	"context"
	"fmt"
	"net/http"
)

type InternalErr struct {
	error
}

func NewInternalErr(error error) InternalErr {
	return InternalErr{error: error}
}

func (e InternalErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusInternalServerError)
}

type BadDTOErr struct {
	error
}

func NewBadDTOErr(format string, args ...any) BadDTOErr {
	return BadDTOErr{error: fmt.Errorf(format, args...)}
}

func (e BadDTOErr) Write(w http.ResponseWriter) {
	http.Error(w, e.Error(), http.StatusBadRequest)
}

// ViewPortError - ошибка при работе ViewPort.
type ViewPortError interface {
	error
	Write(w http.ResponseWriter)
}

// DTO представляет информацию о доменных объектах для внешнего пользователя.
type DTO any

// ViewPort обеспечивает взаимодействие внешних пользователей с доменными объектами.
type ViewPort[D DTO] interface {
	// Get предоставляет информацию о доменных объектах для внешних пользователей.
	Get(ctx context.Context) (D, ViewPortError)
	// Save проверяет корректность и сохраняет информацию, полученную от внешних пользователей.
	Save(ctx context.Context, dto D) ViewPortError
}
