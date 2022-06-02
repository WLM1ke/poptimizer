package front

import (
	"embed"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"html/template"
	"io/fs"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

const (
	_sessionKey = `POSession`
)

//go:embed static
var static embed.FS

// NewFrontend создает обработчики отображающие frontend.
func NewFrontend(logger *lgr.Logger, client *mongo.Client) http.Handler {
	static, err := fs.Sub(static, "static")
	if err != nil {
		logger.Panicf("can't load frontend data -> %s", err)
	}

	index := template.Must(template.ParseFS(static, "*.gohtml"))

	router := chi.NewRouter()

	router.Handle("/", http.RedirectHandler("/tickers", http.StatusMovedPermanently))

	router.Handle(
		"/{file}.css",
		http.StripPrefix("/", http.FileServer(http.FS(static))),
	)

	router.Get("/{page}", indexHandlerFn(logger, index))

	tickers := tickersHandler{
		logger:  logger,
		session: domain.NewSession[selected.Tickers](logger, client),
		tmpl:    extendTemplate(index, static, "tickers/*.gohtml"),
	}
	router.Post("/tickers/session", tickers.handleCreateSession)
	router.Post("/tickers/search", tickers.handleSearch)
	router.Post("/tickers/save", tickers.handleSave)
	router.Post("/tickers/add/{ticker}", tickers.handleAdd)
	router.Post("/tickers/remove/{ticker}", tickers.handleRemove)

	return router
}

func indexHandlerFn(logger *lgr.Logger, index *template.Template) http.HandlerFunc {
	return func(writer http.ResponseWriter, request *http.Request) {
		page := map[string]any{
			"Page":   chi.URLParam(request, "page"),
			"Token":  primitive.NewObjectID().Hex(),
			"Status": "Not edited",
		}

		if err := execTemplate(writer, index, "index", page); err != nil {
			logger.Warnf("can't render template -> %s", err)
		}
	}
}

func extendTemplate(index *template.Template, files fs.FS, pattern string) *template.Template {
	index = template.Must(index.Clone())

	return template.Must(index.ParseFS(files, pattern))
}

func execTemplate(w http.ResponseWriter, tmpl *template.Template, name string, data any) error {
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	err := tmpl.ExecuteTemplate(w, name, data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)

		return fmt.Errorf("can't render template %s -> %w", name, err)
	}

	return nil
}

// Должно вызываться до записи тела ответа.
func addEventToHeader(w http.ResponseWriter, event string) {
	w.Header().Set("HX-Trigger", event)
}
