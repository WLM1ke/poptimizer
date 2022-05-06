package frontend

import (
	"embed"
	"html/template"
	"io/fs"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

//go:embed static
var static embed.FS

// Tickers - пункт меню с информацией о тикерах в портфеле.
const (
	_tickers   = `Tickers`
	_dividends = `Dividends`
	_main      = `Main`
	_metrics   = `Metrics`
	_optimizer = `Optimizer`
	_reports   = `Reports`
)

// Page содержит данные для генерации html-страницы.
type Page struct {
	Menu      string
	SessionID string
	Sidebar   interface{}
	Main      interface{}
	Status    string
}

// NewFrontend создает обработчики отображающие frontend.
func NewFrontend(logger *lgr.Logger, database *mongo.Database, eventBus *bus.EventBus) http.Handler {
	static, err := fs.Sub(static, "static")
	if err != nil {
		logger.Panicf("can't load frontend data -> %s", err)
	}

	index := template.Must(template.ParseFS(static, "index.gohtml"))

	router := chi.NewRouter()

	router.Handle(
		"/{file}.css",
		http.StripPrefix("/", http.FileServer(http.FS(static))),
	)

	tickers := tickersHandler{
		logger:  logger,
		service: services.NewTickersEdit(logger, database, eventBus),
		tmpl:    template.Must(index.ParseFS(static, "tickers/*.gohtml")),
	}

	router.Get("/tickers", tickers.handleIndex)
	router.Post("/tickers/search", tickers.handleSearch)
	router.Post("/tickers/add/{ticker}", tickers.handleAdd)
	router.Post("/tickers/remove/{ticker}", tickers.handleRemove)
	router.Post("/tickers/save", tickers.handleSave)

	return router
}
