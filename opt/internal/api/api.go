package api

import (
	"context"
	"io/fs"
	"net/http"

	"github.com/go-chi/chi"
)

// JSONViewer загружает ExtendedJSON представление данных.
type JSONViewer interface {
	GetJSON(ctx context.Context, group, id string) ([]byte, error)
}

type handler struct {
	mux    *chi.Mux
	viewer JSONViewer
	spa    fs.FS
}

// NewHandler создает обработчики, отображающие frontend и API для получения ExtendedJSON представление данных.
//
// / - SPA, а отдельные разделы динамические отображаются с помощью Alpine.js.
// /api/{group}/{id} - получение данных из определенной группы.
func NewHandler(viewer JSONViewer, spa fs.FS) http.Handler {
	api := handler{
		mux:    chi.NewRouter(),
		viewer: viewer,
		spa:    spa,
	}

	api.registerJSONHandler()

	return &api
}

func (f handler) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	f.mux.ServeHTTP(writer, request)
}
