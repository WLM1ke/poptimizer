package front

import (
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/go-chi/chi"
)

const _updateSearchEvent = `UpdateSearchEvent`

type tickersHandler struct {
	logger  *lgr.Logger
	session *domain.Session[selected.Tickers]
	tmpl    *template.Template
}

func (h *tickersHandler) handleCreateSession(writer http.ResponseWriter, request *http.Request) {
	token := request.PostFormValue(_sessionKey)
	id := selected.ID()

	if err := h.session.Init(request.Context(), token, id); err != nil {
		h.logger.Warnf("can't create token -> %s", err)
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}

	data, err := h.session.Acquire(token)
	defer h.session.Release()

	if err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := execTemplate(writer, h.tmpl, "session", data.Selected()); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleSearch(writer http.ResponseWriter, request *http.Request) {
	token := request.PostFormValue(_sessionKey)
	prefix := request.PostFormValue("prefix")

	data, err := h.session.Acquire(token)
	defer h.session.Release()

	if err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := execTemplate(writer, h.tmpl, "search", data.SearchNotSelected(prefix)); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleSave(writer http.ResponseWriter, request *http.Request) {
	token := request.PostFormValue(_sessionKey)

	if err := h.session.Save(request.Context(), token); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := execTemplate(writer, h.tmpl, "status", "Saved successfully"); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleAdd(writer http.ResponseWriter, request *http.Request) {
	token := request.PostFormValue(_sessionKey)
	ticker := chi.URLParam(request, "ticker")

	data, err := h.session.Acquire(token)
	defer h.session.Release()

	if err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := data.Add(ticker); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	addEventToHeader(writer, _updateSearchEvent)

	if err := execTemplate(writer, h.tmpl, "main", data.Selected()); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}

	if err := execTemplate(writer, h.tmpl, "status", "Edited"); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleRemove(writer http.ResponseWriter, request *http.Request) {
	token := request.PostFormValue(_sessionKey)
	ticker := chi.URLParam(request, "ticker")

	data, err := h.session.Acquire(token)
	defer h.session.Release()

	if err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := data.Remove(ticker); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	addEventToHeader(writer, _updateSearchEvent)

	if err := execTemplate(writer, h.tmpl, "main", data.Selected()); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}

	if err := execTemplate(writer, h.tmpl, "status", "Edited"); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}
