package frontend

import (
	"fmt"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"

	"go.mongodb.org/mongo-driver/bson/primitive"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

type tickersHandler struct {
	logger  *lgr.Logger
	service *services.TickersEdit
	tmpl    *template.Template
}

func (h *tickersHandler) handleIndex(responseWriter http.ResponseWriter, request *http.Request) {
	SessionID := primitive.NewObjectID().Hex()

	tickers, err := h.service.GetTickers(request.Context(), SessionID)
	if err != nil {
		h.logger.Warnf("Server: can't load portfolio tickers -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)

		return
	}

	page := Page{
		Menu:      _tickers,
		SessionID: SessionID,
		Main:      tickers,
		Status:    "not edited",
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.tmpl.ExecuteTemplate(responseWriter, "index", page); err != nil {
		h.logger.Warnf("Server: can't render tmpl template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
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

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.tmpl.ExecuteTemplate(responseWriter, "search", tickers); err != nil {
		h.logger.Warnf("Server: can't render search template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
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

	page := Page{
		Main:   tickers,
		Status: "edited",
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.tmpl.ExecuteTemplate(responseWriter, "change", page); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
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

	page := Page{
		Main:   tickers,
		Status: "edited",
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.tmpl.ExecuteTemplate(responseWriter, "change", page); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *tickersHandler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	n, err := h.service.Save(
		request.Context(),
		request.PostForm.Get("sessionID"),
	)

	status := fmt.Sprintf("%d tickers saved sucsessfully", n)

	if err != nil {
		h.logger.Warnf("Server: can't save portfolio -> %s", err)

		responseWriter.WriteHeader(http.StatusInternalServerError)

		status = fmt.Sprintf("%d tickers saved with error - %s", n, err)
	}

	page := Page{Status: status}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.tmpl.ExecuteTemplate(responseWriter, "status", page); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}
