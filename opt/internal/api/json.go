package api

import (
	"net/http"

	"github.com/go-chi/chi"
)

func (h handler) registerJSONHandler() {
	h.mux.Get("/api/{group}/{id}", h.jsonGet)
}

func (h handler) jsonGet(writer http.ResponseWriter, request *http.Request) {
	group := chi.URLParam(request, "group")
	id := chi.URLParam(request, "id")

	json, err := h.viewer.GetJSON(request.Context(), group, id)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	writer.Header().Set("Content-Type", "application/json; charset=utf-8")
	_, _ = writer.Write(json)
}
