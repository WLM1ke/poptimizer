package front

import (
	"embed"
	"html/template"
	"io/fs"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/alexedwards/scs/v2"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

const _sessionExp = time.Minute * 5

//go:embed static
var static embed.FS

// NewFrontend создает обработчики отображающие frontend.
func NewFrontend(logger *lgr.Logger, client *mongo.Client, pub domain.Publisher) http.Handler {
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

	tickers := handler[selected.TickersState]{
		logger: logger,
		smg:    smg,
		ctrl:   selected.NewTickersController(domain.NewRepo[selected.Tickers](client), pub),
		tmpl:   extendTemplate(index, static, "tickers/*.gohtml"),
		page:   "tickers",
	}
	router.Post("/tickers", tickers.ServeHTTP)
	router.Post("/tickers/{cmd}", tickers.ServeHTTP)

	return smg.LoadAndSave(router)
}

func indexHandlerFn(logger *lgr.Logger, index *template.Template) http.HandlerFunc {
	return func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "text/html; charset=UTF-8")

		err := index.ExecuteTemplate(writer, "index", chi.URLParam(request, "page"))
		if err != nil {
			http.Error(writer, err.Error(), http.StatusInternalServerError)

			logger.Warnf("can't render template index -> %s", err)
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
