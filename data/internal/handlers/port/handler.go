package port

import (
	"fmt"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

type handler struct {
	logger *lgr.Logger

	service *portfolioTickersEdit

	index     *template.Template
	search    *template.Template
	portfolio *template.Template
	save      *template.Template
}

func (h *handler) handleIndex(responseWriter http.ResponseWriter, request *http.Request) {
	ctx := request.Context()

	tickers, err := h.service.GetTickers(ctx)
	if err != nil {
		h.logger.Warnf("Server: can't load portfolio tickers -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)

		return
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.index.Execute(responseWriter, tickers); err != nil {
		h.logger.Warnf("Server: can't render index template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleSearch(responseWriter http.ResponseWriter, request *http.Request) {
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

	if err := h.search.Execute(responseWriter, tickers); err != nil {
		h.logger.Warnf("Server: can't render search template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleAdd(responseWriter http.ResponseWriter, request *http.Request) { //nolint:dupl
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
	// TODO: как-то должен обновляться список тикеров на добавление
	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.portfolio.Execute(responseWriter, tickers); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleRemove(responseWriter http.ResponseWriter, request *http.Request) { //nolint:dupl
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

	// TODO: как-то должен обновляться список тикеров на добавление
	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.portfolio.Execute(responseWriter, tickers); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}

func (h *handler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		h.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	n, err := h.service.Save(
		request.Context(),
		request.PostForm.Get("sessionID"),
	)

	status := fmt.Sprintf("Saved successfully %d tickers", n)

	if err != nil {
		h.logger.Warnf("Server: can't save portfolio -> %s", err)

		status = fmt.Sprintf("Error occured - %s", err)
	}

	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")

	if err := h.save.Execute(responseWriter, status); err != nil {
		h.logger.Warnf("Server: can't render portfolio template -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
	}
}
