package view

import (
	"embed"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"html/template"
	"net/http"
)

//go:embed resources
var res embed.FS

const _path = "resources/index.html"

type page struct {
	Ticker string
	Rows   []domain.RawDiv
}

func editHandler(logger *lgr.Logger, read repo.Read[domain.RawDiv]) http.Handler {
	router := chi.NewRouter()
	router.Get("/{ticker}", func(w http.ResponseWriter, r *http.Request) {
		ticker := chi.URLParam(r, "ticker")

		div, err := read.Get(r.Context(), domain.NewID(raw_div.Group, ticker))
		if err != nil {
			logger.Warnf("Server: can't load dividends -> %s", err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}

		page := page{
			Ticker: ticker,
			Rows:   div.Rows(),
		}

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
