package front

import (
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/go-chi/chi"
)

func (f Frontend) registerJSON() {
	f.mux.Get("/api/{group}/{ticker}", f.jsonGet)
}

func (f Frontend) jsonGet(writer http.ResponseWriter, request *http.Request) {
	qid := domain.QID{
		Sub:   data.Subdomain,
		Group: chi.URLParam(request, "group"),
		ID:    chi.URLParam(request, "ticker"),
	}

	json, err := f.json.GetJSON(request.Context(), qid)
	if err != nil {
		f.logger.Warnf("Server: can't get data from repo -> %s", err)
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	writer.Header().Set("Content-Type", "application/json; charset=utf-8")

	_, err = writer.Write(json)
	if err != nil {
		f.logger.Warnf("Server: can't write respond -> %s", err)
	}
}
