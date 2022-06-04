package front

import (
	"embed"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/alexedwards/scs/v2"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

const _sessionExp = time.Minute * 5

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

	smg := makeSessionManager(logger)

	tickers := tickersHandler{
		logger: logger,
		tmpl:   extendTemplate(index, static, "tickers/*.gohtml"),
		smg:    smg,
		repo:   domain.NewRepo[selected.Tickers](client),
	}
	router.Post("/tickers", tickers.handleIndex)
	router.Post("/tickers/search", tickers.handleSearch)
	router.Post("/tickers/save", tickers.handleSave)
	router.Post("/tickers/add/{ticker}", tickers.handleAdd)
	router.Post("/tickers/remove/{ticker}", tickers.handleRemove)

	return smg.LoadAndSave(router)
}

func indexHandlerFn(logger *lgr.Logger, index *template.Template) http.HandlerFunc {
	return func(writer http.ResponseWriter, request *http.Request) {
		page := map[string]any{
			"Page":  chi.URLParam(request, "page"),
			"Token": primitive.NewObjectID().Hex(),
		}

		if err := execTemplate(writer, index, "index", page); err != nil {
			logger.Warnf("can't render template -> %s", err)
		}
	}
}

func makeSessionManager(logger *lgr.Logger) *scs.SessionManager {
	smg := scs.New()
	smg.IdleTimeout = _sessionExp
	smg.ErrorFunc = func(writer http.ResponseWriter, request *http.Request, err error) {
		logger.WithPrefix("Server").Warnf("session error %s", err)
		http.Error(writer, err.Error(), http.StatusInternalServerError)
	}
	smg.Cookie.Persist = false

	return smg
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
