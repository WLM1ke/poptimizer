package frontend

import (
	"fmt"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

type tickersHandler struct {
	logger  *lgr.Logger
	service *services.TickersEdit
	tmpl    *template.Template
}

func (h *tickersHandler) handleIndex(responseWriter http.ResponseWriter, request *http.Request) {
	SessionID := createSessionID()

	tickers, err := h.service.GetTickers(request.Context(), SessionID)
	if err != nil {
		h.logger.Warnf("Server: can't load portfolio tickers -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)

		return
	}

	page := page{
		Menu:      _tickers,
		SessionID: SessionID,
		Main:      tickers,
		Status:    "not edited",
	}

	if err := execTemplate(h.tmpl, "index", page, responseWriter); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleSearch(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	tickers, err := h.service.SearchTickers(
		request.PostForm.Get("sessionID"),
		request.PostForm.Get("pattern"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't find tickers -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	if err := execTemplate(h.tmpl, "search", tickers, responseWriter); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleAdd(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	tickers, err := h.service.AddTicker(
		request.PostForm.Get("sessionID"),
		chi.URLParam(request, "ticker"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't add ticker -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	page := page{
		Main:   tickers,
		Status: "edited",
	}

	if err := execTemplate(h.tmpl, "change", page, responseWriter); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleRemove(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	tickers, err := h.service.RemoveTicker(
		request.PostForm.Get("sessionID"),
		chi.URLParam(request, "ticker"),
	)
	if err != nil {
		h.logger.Warnf("Server: can't remove ticker -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	page := page{
		Main:   tickers,
		Status: "edited",
	}

	if err := execTemplate(h.tmpl, "change", page, responseWriter); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}

func (h *tickersHandler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	count, err := h.service.Save(
		request.Context(),
		request.PostForm.Get("sessionID"),
	)

	status := fmt.Sprintf("%d tickers saved sucsessfully", count)

	if err != nil {
		h.logger.Warnf("Server: can't save portfolio -> %s", err)

		responseWriter.WriteHeader(http.StatusInternalServerError)

		status = fmt.Sprintf("%d tickers saved with error - %s", count, err)
	}

	page := page{Status: status}

	if err := execTemplate(h.tmpl, "status", page, responseWriter); err != nil {
		h.logger.Warnf("Server: can't render template -> %s", err)
	}
}
