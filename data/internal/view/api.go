package view

import (
	"errors"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

// jsonHandler основной обработчик отдающий данные в формате BSON для http-сервера.
func jsonHandler(logger *lgr.Logger, viewer repo.JSONViewer) http.Handler {
	router := chi.NewRouter()
	router.Get("/{group}/{name}", func(w http.ResponseWriter, r *http.Request) {
		group := chi.URLParam(r, "group")
		name := chi.URLParam(r, "name")

		ctx := r.Context()

		json, err := viewer.GetJSON(ctx, domain.NewID(group, name))
		switch {
		case errors.Is(err, repo.ErrTableNotFound):
			logger.Warnf("Server: can't get data from repo -> %s", err)
			http.NotFound(w, r)
		case err != nil:
			logger.Warnf("Server: can't get data from repo -> %s", err)
			http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		default:
			w.Header().Set("Content-Type", "application/json; charset=utf-8")
			_, err = w.Write(json)
			if err != nil {
				logger.Warnf("Server: can't write respond -> %s", err)
			}
		}
	})

	return router
}
