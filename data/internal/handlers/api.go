package handlers

import (
	"errors"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

// newJSONHandler основной обработчик отдающий данные в формате BSON для http-сервера.
func newJSONHandler(logger *lgr.Logger, viewer repo.JSONViewer) http.Handler {
	router := chi.NewRouter()
	pattern := "/{group}/{ticker}"
	router.Get(pattern, func(responseWriter http.ResponseWriter, request *http.Request) {
		group := chi.URLParam(request, "group")
		name := chi.URLParam(request, "ticker")

		ctx := request.Context()

		json, err := viewer.GetJSON(ctx, domain.NewID(group, name))
		switch {
		case errors.Is(err, repo.ErrTableNotFound):
			logger.Warnf("Server: can't get data from repo -> %s", err)
			http.NotFound(responseWriter, request)
		case err != nil:
			logger.Warnf("Server: can't get data from repo -> %s", err)
			http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
		default:
			responseWriter.Header().Set("Content-Type", "application/json; charset=utf-8")
			_, err = responseWriter.Write(json)
			if err != nil {
				logger.Warnf("Server: can't write respond -> %s", err)
			}
		}
	})

	return router
}
