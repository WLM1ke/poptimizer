package api

import (
	"embed"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"html/template"
	"net/http"
)

//go:embed resources
var res embed.FS

const _path = "resources/index.html"

func editHandler(logger *lgr.Logger) http.Handler {
	router := chi.NewRouter()
	router.Get("/{ticker}", func(w http.ResponseWriter, r *http.Request) {
		ticker := chi.URLParam(r, "ticker")

		var page = struct {
			Ticker string
			Text   string
		}{ticker, "Тут дивиденды!"}

		tpl, err := template.ParseFS(res, _path)
		if err != nil {
			logger.Warnf("Server: dividends edit page template not found in pages cache -> %s", err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}

		if err := tpl.Execute(w, page); err != nil {
			logger.Warnf("Server: can't execute dividends edit page template -> %s", err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "text/html; charset=UTF-8")
		w.WriteHeader(http.StatusOK)
	})

	return router
}
