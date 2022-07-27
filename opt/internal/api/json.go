package api

import (
	"net/http"

	"github.com/go-chi/chi"
)

func (f handler) registerJSONHandler() {
	f.mux.Get("/api/{group}/{id}", f.jsonGet)
}

func (f handler) jsonGet(writer http.ResponseWriter, request *http.Request) {
	group := chi.URLParam(request, "group")
	id := chi.URLParam(request, "id")

	json, err := f.viewer.GetJSON(request.Context(), group, id)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	writer.Header().Set("Content-Type", "application/json; charset=utf-8")
	_, _ = writer.Write(json)
}
