package edit

import (
	_ "embed"
	"html/template"
	"net/http"
	"time"

	"github.com/jellydator/ttlcache/v3"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
)

var (
	//go:embed resources/index.html
	_index string
	//go:embed resources/row.html
	_row string
)

// Handler - обрабатывает запросы связанные с изменением дивидендов.
func Handler(logger *lgr.Logger, read repo.Read[domain.RawDiv]) http.Handler {
	handler := handler{
		logger: logger,
		repo:   read,
		cache:  ttlcache.New[string, *model](ttlcache.WithTTL[string, *model](10 * time.Minute)),
		index:  template.Must(template.New("index").Parse(_index)),
		row:    template.Must(template.New("row").Parse(_row)),
	}

	router := chi.NewRouter()
	router.Get("/{ticker}", handler.handleIndex)
	router.Post("/{ticker}/add", handler.handleAddRow)

	return router
}
