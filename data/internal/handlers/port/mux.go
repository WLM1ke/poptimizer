package port

import (
	"embed"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

//go:embed resources
var _resources embed.FS

// NewPortfolioTickersHandler - обрабатывает запросы связанные с изменением дивидендов.
func NewPortfolioTickersHandler(logger *lgr.Logger, database *mongo.Database, eventBus *bus.EventBus) http.Handler {
	handler := handler{
		logger:    logger,
		service:   newPortfolioTickersEdit(logger, database, eventBus),
		index:     template.Must(template.ParseFS(_resources, "resources/index.gohtml")),
		search:    template.Must(template.ParseFS(_resources, "resources/search.gohtml")),
		portfolio: template.Must(template.ParseFS(_resources, "resources/portfolio.gohtml")),
		save:      template.Must(template.ParseFS(_resources, "resources/save.gohtml")),
	}

	router := chi.NewRouter()
	router.Get("/tickers", handler.handleIndex)
	router.Post("/search", handler.handleSearch)
	router.Post("/add/{ticker}", handler.handleAdd)
	router.Post("/remove/{ticker}", handler.handleRemove)
	router.Post("/save", handler.handleSave)

	return router
}
