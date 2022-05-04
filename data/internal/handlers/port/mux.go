package port

import (
	"embed"
	"html/template"
	"io/fs"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

//go:embed static
var _resources embed.FS

// NewPortfolioTickersHandler - обрабатывает запросы связанные с изменением дивидендов.
func NewPortfolioTickersHandler(logger *lgr.Logger, database *mongo.Database, eventBus *bus.EventBus) http.Handler {
	static, err := fs.Sub(_resources, "static")
	if err != nil {
		logger.Panicf("can't find template dir -> %s", err)
	}

	handler := handler{
		logger:  logger,
		service: newPortfolioTickersEdit(logger, database, eventBus),
		tmpl:    template.Must(template.ParseFS(static, "*/*.gohtml")),
	}

	router := chi.NewRouter()
	router.Get("/tickers", handler.handleIndex)
	router.Post("/tickers/search", handler.handleSearch)
	router.Post("/tickers/add/{ticker}", handler.handleAdd)
	router.Post("/tickers/remove/{ticker}", handler.handleRemove)
	router.Post("/tickers/save", handler.handleSave)
	router.Handle("/tickers/{file}.css", http.StripPrefix("/tickers/", http.FileServer(http.FS(static))))

	return router
}
