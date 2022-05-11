package frontend

import (
	"fmt"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

type dividendsHandler struct {
	logger  *lgr.Logger
	service *services.RawDivEdit
	tmpl    *template.Template
}

func (d *dividendsHandler) handleIndex(responseWriter http.ResponseWriter, request *http.Request) {
	SessionID := createSessionID()

	err := d.service.StartSession(request.Context(), SessionID)
	if err != nil {
		d.logger.Warnf("Server: can't start session -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)

		return
	}

	page := page{
		Menu:      _dividends,
		SessionID: SessionID,
		Status:    "not edited",
	}

	if err := execTemplate(d.tmpl, "index", page, responseWriter); err != nil {
		d.logger.Warnf("Server: %s", err)
	}
}

func (d *dividendsHandler) handleFind(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		d.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	tickers, err := d.service.FindTicker(
		request.PostForm.Get("sessionID"),
		request.PostForm.Get("pattern"),
	)
	if err != nil {
		d.logger.Warnf("Server: can't find tickers -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	if err := execTemplate(d.tmpl, "find", tickers, responseWriter); err != nil {
		d.logger.Warnf("Server: %s", err)
	}
}

func (d *dividendsHandler) handleSelect(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		d.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	divInfo, err := d.service.GetDividends(
		request.Context(),
		request.PostForm.Get("sessionID"),
		chi.URLParam(request, "ticker"),
	)
	if err != nil {
		d.logger.Warnf("Server: can't load divInfo -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	page := page{
		Main:   divInfo,
		Status: "not edited",
	}

	if err := execTemplate(d.tmpl, "dividends", page, responseWriter); err != nil {
		d.logger.Warnf("Server: %s", err)
	}
}

func (d *dividendsHandler) handleAddRow(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		d.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	divInfo, err := d.service.AddRow(
		request.PostForm.Get("sessionID"),
		request.PostForm.Get("date"),
		request.PostForm.Get("value"),
		request.PostForm.Get("currency"),
	)
	if err != nil {
		d.logger.Warnf("Server: can't add row -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	page := page{
		Main:   divInfo,
		Status: "edited",
	}

	if err := execTemplate(d.tmpl, "add", page, responseWriter); err != nil {
		d.logger.Warnf("Server: %s", err)
	}
}

func (d *dividendsHandler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		d.logger.Warnf("Server: can't parse request form -> %s", err)
		http.Error(responseWriter, err.Error(), http.StatusBadRequest)

		return
	}

	count, err := d.service.Save(request.Context(), request.PostForm.Get("sessionID"))

	status := fmt.Sprintf("%d dividends saved sucsessfully", count)

	if err != nil {
		d.logger.Warnf("Server: can't save dividends -> %s", err)

		responseWriter.WriteHeader(http.StatusInternalServerError)

		status = fmt.Sprintf("%d dividends saved with error - %s", count, err)
	}

	page := page{Status: status}

	if err := execTemplate(d.tmpl, "status", page, responseWriter); err != nil {
		d.logger.Warnf("Server: %s", err)
	}
}
