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

// NewFrontend создает обработчики отображающие frontend.
func NewFrontend(logger *lgr.Logger, database *mongo.Database, eventBus *bus.EventBus) http.Handler {
	static, err := fs.Sub(static, "static")
	if err != nil {
		logger.Panicf("can't load frontend data -> %s", err)
	}

	index := template.Must(template.ParseFS(static, "index.gohtml"))

	router := chi.NewRouter()

	router.Handle("/", http.RedirectHandler("/tickers", http.StatusMovedPermanently))

	router.Handle(
		"/{file}.css",
		http.StripPrefix("/", http.FileServer(http.FS(static))),
	)

	tickers := tickersHandler{
		logger:  logger,
		service: services.NewTickersEdit(logger, database, eventBus),
		tmpl:    extendTemplate(index, static, "tickers/*.gohtml"),
	}

	router.Get("/tickers", tickers.handleIndex)
	router.Post("/tickers/search", tickers.handleSearch)
	router.Post("/tickers/add/{ticker}", tickers.handleAdd)
	router.Post("/tickers/remove/{ticker}", tickers.handleRemove)
	router.Post("/tickers/save", tickers.handleSave)

	dividends := dividendsHandler{
		logger:  logger,
		service: services.NewRawDivEdit(logger, database, eventBus),
		tmpl:    extendTemplate(index, static, "dividends/*.gohtml"),
	}

	router.Get("/dividends", dividends.handleIndex)
	router.Post("/dividends/find", dividends.handleFind)
	router.Post("/dividends/select/{ticker}", dividends.handleSelect)

	return router
}
