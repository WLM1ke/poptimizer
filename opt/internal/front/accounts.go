package front

import (
	"encoding/json"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/port"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/go-chi/chi"
)

func (f Frontend) registerAccountsHandlers() {
	f.mux.Get("/accounts", f.accountsGetNames)
	f.mux.Get("/accounts/{name}", f.accountsGetAccount)
	f.mux.Post("/accounts/{name}", f.accountsCreate)
	f.mux.Put("/accounts/{name}", f.accountsUpdate)
	f.mux.Delete("/accounts/{name}", f.accountsDelete)
}

func (f Frontend) accountsGetNames(writer http.ResponseWriter, request *http.Request) {
	dto, err := f.accounts.GetAccountNames(request.Context())
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(f.logger, writer, dto)
}

func (f Frontend) accountsCreate(writer http.ResponseWriter, request *http.Request) {
	err := f.accounts.CreateAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusCreated)
}

func (f Frontend) accountsDelete(writer http.ResponseWriter, request *http.Request) {
	err := f.accounts.DeleteAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusNoContent)
}

func (f Frontend) accountsGetAccount(writer http.ResponseWriter, request *http.Request) {
	dto, err := f.accounts.GetAccount(request.Context(), chi.URLParam(request, "name"))
	if err != nil {
		err.Write(writer)

		return
	}

	servers.WriteJSON(f.logger, writer, dto)
}

func (f Frontend) accountsUpdate(writer http.ResponseWriter, request *http.Request) {
	var dto port.UpdateDTO

	if err := json.NewDecoder(request.Body).Decode(&dto); err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		f.logger.Warnf("can't decode accounts update dto -> %s", err)

		return
	}

	if err := f.accounts.UpdateAccount(request.Context(), chi.URLParam(request, "name"), dto); err != nil {
		err.Write(writer)

		return
	}

	writer.WriteHeader(http.StatusNoContent)
}
