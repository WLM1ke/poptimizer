package div

import (
	"embed"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"go.mongodb.org/mongo-driver/mongo"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

//go:embed resources
var _resources embed.FS

// NewEditHandler - обрабатывает запросы связанные с изменением дивидендов.
func NewEditHandler(logger *lgr.Logger, database *mongo.Database, bus *bus.EventBus) http.Handler {
	handler := handler{
		logger:  logger,
		service: newRawDivEdit(logger, database, bus),
		index:   template.Must(template.ParseFS(_resources, "resources/index.gohtml")),
		add:     template.Must(template.ParseFS(_resources, "resources/add.gohtml")),
		reload:  template.Must(template.ParseFS(_resources, "resources/reload.gohtml")),
		save:    template.Must(template.ParseFS(_resources, "resources/save.gohtml")),
	}

	router := chi.NewRouter()
	router.Get("/{ticker}", handler.handleIndex)
	router.Post("/{ticker}/add", handler.handleAddRow)
	router.Post("/{ticker}/reload", handler.handleReload)
	router.Post("/{ticker}/save", handler.handleSave)

	return router
}
