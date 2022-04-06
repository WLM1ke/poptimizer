package edit

import (
	"errors"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

const _sessionID = `SessionID`

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
		h.logger.Warnf("Server: can't load dividends -> %s", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)

		return
	}

	cookie := http.Cookie{
		Name:     _sessionID,
		Value:    model.SessionID,
		Path:     r.RequestURI,
		MaxAge:   0,
		Secure:   false,
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
	}

	http.SetCookie(w, &cookie)
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.index.Execute(w, model); err != nil {
		h.logger.Warnf("Server: can't render index template -> %s", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleAddRow(rw http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(rw, err.Error(), http.StatusBadRequest)

		return
	}

	if err := r.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(rw, err.Error(), http.StatusBadRequest)

		return
	}

	row, err := h.service.AddRow(
		cookie.Value,
		r.PostForm.Get("date"),
		r.PostForm.Get("value"),
		r.PostForm.Get("currency"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't add row -> %s", err)
		http.Error(rw, err.Error(), http.StatusBadRequest)

		return
	}

	rw.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.add.Execute(rw, row); err != nil {
		h.logger.Warnf("Server: can't render add template -> %s", err)
		http.Error(rw, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleReload(rw http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(rw, err.Error(), http.StatusBadRequest)

		return
	}

	div, err := h.service.Reload(r.Context(), cookie.Value)
	if err != nil {
		h.logger.Warnf("Server: can't reload page -> %s", err)
		http.Error(rw, err.Error(), http.StatusBadRequest)

		return
	}

	rw.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.reload.Execute(rw, div); err != nil {
		h.logger.Warnf("Server: can't render reload template -> %s", err)
		http.Error(rw, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleSave(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(_sessionID)
	if errors.Is(err, http.ErrNoCookie) {
		h.logger.Warnf("Server: no cookie in request")
		http.Error(w, err.Error(), http.StatusBadRequest)

		return
	}

	status := h.service.Save(r.Context(), cookie.Value)

	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.save.Execute(w, status); err != nil {
		h.logger.Warnf("Server: can't render save template -> %s", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
