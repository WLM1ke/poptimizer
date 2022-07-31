package api

import (
	"context"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/port"
	"github.com/go-chi/chi"
)

// JSONViewer загружает ExtendedJSON представление данных.
type JSONViewer interface {
	// GetPortfolio загружает ExtendedJSON с датой последнего портфеля и набором входящих в него тикеров.
	GetPortfolio(ctx context.Context) ([]byte, error)
	// GetData загружает ExtendedJSON представление данных.
	GetData(ctx context.Context, group, id string) ([]byte, error)
}

type handler struct {
	mux    *chi.Mux
	viewer JSONViewer
	spa    fs.FS

	tickers   *securities.EditService
	dividends *raw.EditRawService
	accounts  *port.AccEditService
	portfolio *port.ViewPortfolioService
}

// NewHandler создает обработчики, отображающие frontend и API для получения ExtendedJSON представления данных.
//
// / - SPA, а отдельные разделы динамические отображаются с помощью Alpine.js.
// /api/{group}/{id} - получение данных из определенной группы.
func NewHandler(
	viewer JSONViewer,
	spa fs.FS,
	tickers *securities.EditService,
	dividends *raw.EditRawService,
	accounts *port.AccEditService,
	portfolio *port.ViewPortfolioService,
) http.Handler {
	api := handler{
		mux:       chi.NewRouter(),
		viewer:    viewer,
		spa:       spa,
		tickers:   tickers,
		dividends: dividends,
		accounts:  accounts,
		portfolio: portfolio,
	}

	api.registerJSONHandler()

	api.registerFrontend()
	api.registerTickersHandlers()
	api.registerDividendsHandlers()
	api.registerAccountsHandlers()
	api.registerPortfolioHandlers()

	return &api
}

func (h handler) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	h.mux.ServeHTTP(writer, request)
}

func (h handler) registerFrontend() {
	h.mux.Handle("/{file}", http.StripPrefix("/", http.FileServer(http.FS(h.spa))))

	index := template.Must(template.ParseFS(h.spa, "index.html"))

	h.mux.Get("/", func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "text/html;charset=UTF-8")

		err := index.Execute(writer, nil)
		if err != nil {
			http.Error(writer, fmt.Sprintf("can't render template -> %s", err), http.StatusInternalServerError)
		}
	})
}
