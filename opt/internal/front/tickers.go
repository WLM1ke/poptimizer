package front

import (
	"fmt"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/alexedwards/scs/v2"
	"github.com/go-chi/chi"
)

const (
	_tickersKey       = `tickersKey`
	_tickersPrefixKey = `tickersPrefixKey`
	_tickersStatusKey = `tickersStatusKey`
)

type tickersState struct {
	Selected    []string
	Prefix      string
	NotSelected []string
	Status      string
}

type tickersHandler struct {
	logger *lgr.Logger
	tmpl   *template.Template
	smg    *scs.SessionManager
	repo   domain.ReadWriteRepo[selected.Tickers]
}

func (h *tickersHandler) render(tmpl string, writer http.ResponseWriter, request *http.Request) {
	if !h.smg.Exists(request.Context(), _tickersKey) {
		agg, err := h.repo.Get(request.Context(), selected.ID())
		if err != nil {
			h.logger.Warnf(err.Error())
			http.Error(writer, err.Error(), http.StatusBadRequest)

			return
		}

		h.smg.Put(request.Context(), _tickersKey, agg)
	}

	if !h.smg.Exists(request.Context(), _tickersStatusKey) {
		h.smg.Put(request.Context(), _tickersStatusKey, "Not edited")
	}

	agg, ok := h.smg.Get(request.Context(), _tickersKey).(domain.Aggregate[selected.Tickers])
	if !ok {
		err := fmt.Errorf("can't decode session data")
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	prefix := h.smg.GetString(request.Context(), _tickersPrefixKey)

	state := tickersState{
		Selected:    agg.Entity.Selected(),
		Prefix:      prefix,
		NotSelected: agg.Entity.SearchNotSelected(prefix),
		Status:      h.smg.GetString(request.Context(), _tickersStatusKey),
	}

	if err := execTemplate(writer, h.tmpl, tmpl, state); err != nil {
		h.logger.Warnf("Server: can't render template %s -> %s", tmpl, err)
	}
}

func (h *tickersHandler) handleIndex(writer http.ResponseWriter, request *http.Request) {
	h.render("index", writer, request)
}

func (h *tickersHandler) handleSearch(writer http.ResponseWriter, request *http.Request) {
	h.smg.Put(request.Context(), _tickersPrefixKey, request.PostFormValue("prefix"))

	h.render("update", writer, request)
}

func (h *tickersHandler) handleSave(writer http.ResponseWriter, request *http.Request) {
	agg, ok := h.smg.Get(request.Context(), _tickersKey).(domain.Aggregate[selected.Tickers])
	if !ok {
		err := fmt.Errorf("can't decode session data")
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	if err := h.repo.Save(request.Context(), agg); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	h.smg.Remove(request.Context(), _tickersKey)
	h.smg.Put(request.Context(), _tickersStatusKey, "Saved successfully")

	h.render("update", writer, request)
}

func (h *tickersHandler) handleAdd(writer http.ResponseWriter, request *http.Request) { //nolint:dupl
	agg, ok := h.smg.Get(request.Context(), _tickersKey).(domain.Aggregate[selected.Tickers])
	if !ok {
		err := fmt.Errorf("can't decode session data")
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	ticker := chi.URLParam(request, "ticker")

	if err := agg.Entity.Add(ticker); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	h.smg.Put(request.Context(), _tickersKey, agg)
	h.smg.Put(request.Context(), _tickersStatusKey, "Edited")

	h.render("update", writer, request)
}

func (h *tickersHandler) handleRemove(writer http.ResponseWriter, request *http.Request) { //nolint:dupl
	agg, ok := h.smg.Get(request.Context(), _tickersKey).(domain.Aggregate[selected.Tickers])
	if !ok {
		err := fmt.Errorf("can't decode session data")
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	ticker := chi.URLParam(request, "ticker")

	if err := agg.Entity.Remove(ticker); err != nil {
		h.logger.Warnf(err.Error())
		http.Error(writer, err.Error(), http.StatusBadRequest)

		return
	}

	h.smg.Put(request.Context(), _tickersKey, agg)
	h.smg.Put(request.Context(), _tickersStatusKey, "Edited")

	h.render("update", writer, request)
}
