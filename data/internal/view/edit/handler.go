package edit

import (
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

type handler struct {
	logger *lgr.Logger
	repo   repo.Read[domain.RawDiv]

	model *model

	index *template.Template
	row   *template.Template
}

func (h *handler) handleIndex(w http.ResponseWriter, r *http.Request) {
	ticker := chi.URLParam(r, "ticker")

	div, err := h.repo.Get(r.Context(), domain.NewID(raw_div.Group, ticker))
	if err != nil {
		h.logger.Warnf("Server: can't load dividends -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	h.model = &model{
		Ticker: ticker,
		Rows:   div.Rows(),
	}

	if err := h.index.Execute(w, h.model); err != nil {
		h.logger.Warnf("Server: can't render index -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleAddRow(w http.ResponseWriter, r *http.Request) {
	row, err := parseForm(r)
	if err != nil {
		h.logger.Warnf("Server: can't parse form", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	h.model.addRow(row)

	if err := h.row.Execute(w, h.model.Last()); err != nil {
		h.logger.Warnf("Server: can't render index -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}
