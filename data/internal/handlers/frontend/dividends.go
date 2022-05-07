package frontend

import (
	"html/template"
	"net/http"

	"github.com/go-chi/chi"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
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
		d.logger.Warnf("Server: can't render template -> %s", err)
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
		d.logger.Warnf("Server: can't render template -> %s", err)
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
		d.logger.Warnf("Server: can't render template -> %s", err)
	}
}

// func (h *handler) handleAddRow(responseWriter http.ResponseWriter, request *http.Request) {
//	if err := request.ParseForm(); err != nil {
//		h.logger.Warnf("Server: can't parse request form -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusBadRequest)
//
//		return
//	}
//
//	row, err := h.service.AddRow(
//		request.PostForm.Get("sessionID"),
//		request.PostForm.Get("date"),
//		request.PostForm.Get("value"),
//		request.PostForm.Get("currency"),
//	)
//	if err != nil {
//		h.logger.Warnf("Server: can't add row -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusBadRequest)
//
//		return
//	}
//
//	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")
//
//	if err := h.rows.Execute(responseWriter, row); err != nil {
//		h.logger.Warnf("Server: can't render rows template -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
//	}
//}
//
// func (h *handler) handleReload(responseWriter http.ResponseWriter, request *http.Request) {
//	if err := request.ParseForm(); err != nil {
//		h.logger.Warnf("Server: can't parse request form -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusBadRequest)
//
//		return
//	}
//
//	div, err := h.service.Reload(request.Context(), request.PostForm.Get("sessionID"))
//	if err != nil {
//		h.logger.Warnf("Server: can't reload page -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusBadRequest)
//
//		return
//	}
//
//	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")
//
//	if err := h.rows.Execute(responseWriter, div); err != nil {
//		h.logger.Warnf("Server: can't render rows template -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
//	}
//}
//
// func (h *handler) handleSave(responseWriter http.ResponseWriter, request *http.Request) {
//	if err := request.ParseForm(); err != nil {
//		h.logger.Warnf("Server: can't parse request form -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusBadRequest)
//
//		return
//	}
//
//	status := "Saved successfully"
//
//	err := h.service.Save(request.Context(), request.PostForm.Get("sessionID"))
//	if err != nil {
//		status = fmt.Sprintf("Error occurred: %s", err)
//	}
//
//	responseWriter.Header().Set("Content-Type", "text/html; charset=UTF-8")
//
//	if err := h.save.Execute(responseWriter, status); err != nil {
//		h.logger.Warnf("Server: can't render save template -> %s", err)
//		http.Error(responseWriter, err.Error(), http.StatusInternalServerError)
//	}
//}
