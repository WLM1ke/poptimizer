package api

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/go-chi/chi"
)

func (h handler) registerDividendsHandlers() {
	h.mux.Get("/dividends", h.dividendsGetTickers)
	h.mux.Get("/dividends/{ticker}", h.dividendsGetDividends)
	h.mux.Put("/dividends/{ticker}", h.dividendsPutDividends)
}

func (h handler) dividendsGetTickers(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.dividends.GetTickers(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) dividendsGetDividends(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.dividends.GetDividends(request.Context(), chi.URLParam(request, "ticker"))
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) dividendsPutDividends(writer http.ResponseWriter, request *http.Request) {
	defer request.Body.Close()

	var dto raw.SaveDividendsDTO

	if err := json.NewDecoder(request.Body).Decode(&dto); err != nil {
		http.Error(writer, fmt.Sprintf("can't decode dividends dto -> %s", err), http.StatusInternalServerError)

		return
	}

	err := h.dividends.Save(request.Context(), dto)
	if err != nil {
		err.Write(writer)

		return
	}
}
