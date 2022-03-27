package edit

import (
	"fmt"
	"html/template"
	"net/http"
	"strconv"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/raw_div"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
	"github.com/jellydator/ttlcache/v3"
)

const _timeFormat = "2006-01-02"

type handler struct {
	logger *lgr.Logger
	repo   repo.Read[domain.RawDiv]

	cache *ttlcache.Cache[string, *model]

	index  *template.Template
	row    *template.Template
	reload *template.Template
	save   *template.Template
}

func (h *handler) handleIndex(w http.ResponseWriter, r *http.Request) {
	h.cache.DeleteExpired()

	ticker := chi.URLParam(r, "ticker")

	ctx := r.Context()
	id := middleware.GetReqID(ctx)

	div, err := h.repo.Get(ctx, domain.NewID(raw_div.Group, ticker))
	if err != nil {
		h.logger.Warnf("Server: can't load dividends -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	model := &model{
		ID:     id,
		Ticker: ticker,
		Rows:   div.Rows(),
	}

	h.cache.Set(id, model, ttlcache.DefaultTTL)

	if err := h.index.Execute(w, model); err != nil {
		h.logger.Warnf("Server: can't render index -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleAddRow(w http.ResponseWriter, r *http.Request) {
	model := h.loadModelAndAppend(r, true)
	if model == nil {
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	if err := h.row.Execute(w, model.Last()); err != nil {
		h.logger.Warnf("Server: can't render add row -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleReload(w http.ResponseWriter, r *http.Request) {
	model := h.loadModelAndAppend(r, false)
	if model == nil {
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	div, err := h.repo.Get(r.Context(), domain.NewID(raw_div.Group, model.Ticker))
	if err != nil {
		h.logger.Warnf("Server: can't load dividends -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	model.Rows = div.Rows()

	if err := h.reload.Execute(w, model); err != nil {
		h.logger.Warnf("Server: can't render add row -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleSave(w http.ResponseWriter, r *http.Request) {
	model := h.loadModelAndAppend(r, false)
	if model == nil {
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	if err := h.save.Execute(w, fakeSave(model)); err != nil {
		h.logger.Warnf("Server: can't render save data -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) loadModelAndAppend(r *http.Request, addRow bool) *model {
	if err := r.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request -> %s", err)

		return nil
	}

	id := r.PostForm.Get("id")
	item := h.cache.Get(id)

	if item == nil {
		h.logger.Warnf("Server: wrong model id - %s", id)

		return nil
	}

	model := item.Value()

	if !addRow {
		return model
	}

	var (
		err error
		row domain.RawDiv
	)

	row.Date, err = time.Parse(_timeFormat, r.PostForm.Get("date"))

	if err != nil {
		h.logger.Warnf("Server: can't parse request -> %s", err)

		return nil
	}

	row.Value, err = strconv.ParseFloat(r.PostForm.Get("value"), 64)
	if err != nil {
		h.logger.Warnf("Server: can't parse request -> %s", err)

		return nil
	}

	row.Currency = r.PostForm.Get("currency")

	model.addRow(row)

	return model
}

func fakeSave(model *model) string {
	return fmt.Sprintf("Saved successfully: %s - count %d", model.Ticker, len(model.Rows))
}
