package api

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
)

func (h handler) registerTickersHandlers() {
	h.mux.Get("/tickers", h.tickersGet)
	h.mux.Put("/tickers", h.tickersPut)
}

func (h handler) tickersGet(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.tickers.Get(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) tickersPut(writer http.ResponseWriter, request *http.Request) {
	defer request.Body.Close()

	var dto securities.DTO

	if err := json.NewDecoder(request.Body).Decode(&dto); err != nil {
		http.Error(writer, fmt.Sprintf("can't decode dto tickers -> %s", err), http.StatusBadRequest)

		return
	}

	err := h.tickers.Save(request.Context(), dto)
	if err != nil {
		err.Write(writer)

		return
	}
}
