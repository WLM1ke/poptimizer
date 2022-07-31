package api

import (
	"net/http"

	"github.com/go-chi/chi"
)

func (h handler) registerJSONHandler() {
	h.mux.Get("/api/portfolio", h.jsonGetPortfolio)
	h.mux.Get("/api/{group}/{id}", h.jsonGetData)
}

func (h handler) jsonGetPortfolio(writer http.ResponseWriter, request *http.Request) {
	json, err := h.viewer.GetPortfolio(request.Context())
	if err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	writer.Header().Set("Content-Type", "application/json; charset=utf-8")
	_, _ = writer.Write(json)
}

func (h handler) jsonGetData(writer http.ResponseWriter, request *http.Request) {
	group := chi.URLParam(request, "group")
	id := chi.URLParam(request, "id")

	json, err := h.viewer.GetData(request.Context(), group, id)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	if json == nil {
		writer.WriteHeader(http.StatusNoContent)

		return
	}

	writer.Header().Set("Content-Type", "application/json; charset=utf-8")
	_, _ = writer.Write(json)
}
