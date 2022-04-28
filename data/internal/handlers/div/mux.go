package div

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

// NewEditHandler - обрабатывает запросы связанные с изменением дивидендов.
func NewEditHandler(logger *lgr.Logger, database *mongo.Database, eventBus *bus.EventBus) http.Handler {
	handler := handler{
		logger:  logger,
		service: newRawDivEdit(logger, database, eventBus),
		index:   template.Must(template.ParseFS(_resources, "resources/index.gohtml")),
		rows:    template.Must(template.ParseFS(_resources, "resources/rows.gohtml")),
		save:    template.Must(template.ParseFS(_resources, "resources/save.gohtml")),
	}

	router := chi.NewRouter()
	router.Get("/{ticker}", handler.handleIndex)
	router.Post("/{ticker}/add", handler.handleAddRow)
	router.Post("/{ticker}/reload", handler.handleReload)
	router.Post("/{ticker}/save", handler.handleSave)

	return router
}
