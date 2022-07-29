package api

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/port"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/go-chi/chi"
)

func (h handler) registerAccountsHandlers() {
	h.mux.Get("/accounts", h.accountsGetNames)
	h.mux.Get("/accounts/{name}", h.accountsGetAccount)
	h.mux.Post("/accounts/{name}", h.accountsCreate)
	h.mux.Put("/accounts/{name}", h.accountsUpdate)
	h.mux.Delete("/accounts/{name}", h.accountsDelete)
}

func (h handler) accountsGetNames(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.accounts.GetAccountNames(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) accountsCreate(writer http.ResponseWriter, request *http.Request) {
	err := h.accounts.CreateAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusCreated)
}

func (h handler) accountsDelete(writer http.ResponseWriter, request *http.Request) {
	err := h.accounts.DeleteAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusNoContent)
}

func (h handler) accountsGetAccount(writer http.ResponseWriter, request *http.Request) {
	dto, err := h.accounts.GetAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(writer, dto)
}

func (h handler) accountsUpdate(writer http.ResponseWriter, request *http.Request) {
	var dto port.UpdateDTO

	if err := json.NewDecoder(request.Body).Decode(&dto); err != nil {
		http.Error(writer, fmt.Sprintf("can't decode accounts update dto -> %s", err), http.StatusBadRequest)

		return
	}

	if err := h.accounts.UpdateAccount(request.Context(), chi.URLParam(request, "name"), dto); err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusNoContent)
}
