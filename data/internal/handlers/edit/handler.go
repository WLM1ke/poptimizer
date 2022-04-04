package edit

import (
	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"html/template"
	"net/http"
)

type handler struct {
	logger *lgr.Logger

	service *services.RawDivUpdate

	index  *template.Template
	add    *template.Template
	reload *template.Template
	save   *template.Template
}

func (h *handler) handleIndex(w http.ResponseWriter, r *http.Request) {
	ticker := chi.URLParam(r, "ticker")
	ctx := r.Context()

	model, err := h.service.GetByTicker(ctx, ticker)
	if err != nil {
		h.logger.Warnf("Server: can't load dividends %s -> %s", ticker, err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	if err := h.index.Execute(w, model); err != nil {
		h.logger.Warnf("Server: can't render index template -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleAddRow(w http.ResponseWriter, r *http.Request) {
	id := r.Header.Get("X-Request-ID")
	if id == "" {
		h.logger.Warnf("Server: no id in request")
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	if err := r.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	row, err := h.service.AddRow(
		id,
		r.PostForm.Get("date"),
		r.PostForm.Get("value"),
		r.PostForm.Get("currency"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't add row for session id %s-> %s", id, err)
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	if err := h.add.Execute(w, row); err != nil {
		h.logger.Warnf("Server: can't render add template -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleReload(w http.ResponseWriter, r *http.Request) {
	id := r.Header.Get("X-Request-ID")
	if id == "" {
		h.logger.Warnf("Server: no id in request")
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	div, err := h.service.Reload(r.Context(), id)
	if err != nil {
		h.logger.Warnf("Server: can't reload page for session id %s -> %s", id, err)
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	if err := h.reload.Execute(w, div); err != nil {
		h.logger.Warnf("Server: can't render reload template -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}

func (h *handler) handleSave(w http.ResponseWriter, r *http.Request) {
	id := r.Header.Get("X-Request-ID")
	if id == "" {
		h.logger.Warnf("Server: no id in request")
		w.WriteHeader(http.StatusBadRequest)

		return
	}

	status := h.service.Save(r.Context(), id)

	if err := h.save.Execute(w, status); err != nil {
		h.logger.Warnf("Server: can't render save template -> %s", err)
		w.WriteHeader(http.StatusInternalServerError)

		return
	}

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.WriteHeader(http.StatusOK)
}
