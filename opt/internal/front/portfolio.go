package front

import (
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/go-chi/chi"
)

func (f Frontend) registerPortfolioHandlers() {
	f.mux.Get("/portfolio", f.portfolioGetDates)
	f.mux.Get("/portfolio/{date}", f.portfolioGet)
}

func (f Frontend) portfolioGetDates(writer http.ResponseWriter, request *http.Request) {
	dto, err := f.portfolio.GetPortfolioDates(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(f.logger, writer, dto)
}

func (f Frontend) portfolioGet(writer http.ResponseWriter, request *http.Request) {
	dto, err := f.portfolio.GetPortfolio(request.Context(), chi.URLParam(request, "date"))
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(f.logger, writer, dto)
}
