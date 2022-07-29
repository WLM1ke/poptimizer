package api

import (
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/go-chi/chi"
)

func (h handler) registerPortfolioHandlers() {
	h.mux.Get("/portfolio", h.portfolioGetDates)
	h.mux.Get("/portfolio/{date}", h.portfolioGet)
}

func (h handler) portfolioGetDates(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.portfolio.GetDates(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) portfolioGet(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.portfolio.Get(request.Context(), chi.URLParam(request, "date"))
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}
