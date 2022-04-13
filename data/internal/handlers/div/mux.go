package div

import (
	"embed"
	"html/template"
	"net/http"

	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

//go:embed resources
var _resources embed.FS

// NewEditHandler - обрабатывает запросы связанные с изменением дивидендов.
func NewEditHandler(logger *lgr.Logger, service *services.RawDivUpdate) http.Handler {
	handler := handler{
		logger:  logger,
		service: service,
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
