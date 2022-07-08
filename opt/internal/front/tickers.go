package front

import (
	"encoding/json"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
)

func (f Frontend) registerTickersHandlers() {
	f.mux.Get("/tickers", f.tickersGet)
	f.mux.Put("/tickers", f.tickersPut)
}

func (f Frontend) tickersGet(writer http.ResponseWriter, request *http.Request) {
	dto, err := f.tickers.Get(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(f.logger, writer, dto)
}

func (f Frontend) tickersPut(writer http.ResponseWriter, request *http.Request) {
	defer request.Body.Close()

	var dto securities.DTO

	if err := json.NewDecoder(request.Body).Decode(&dto); err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		f.logger.Warnf("can't decode dto tickers -> %s", err)

		return
	}

	err := f.tickers.Save(request.Context(), dto)
	if err != nil {
		err.Write(writer)

		return
	}
}
