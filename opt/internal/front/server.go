package front

import (
	"embed"
	"html/template"
	"io/fs"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/div"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

//go:embed static
var static embed.FS

// Frontend представляет web-интерфейс приложения.
type Frontend struct {
	mux    *chi.Mux
	files  fs.FS
	logger *lgr.Logger

	tickers   *securities.Service
	dividends *div.Service
}

// NewFrontend создает обработчики, отображающие frontend.
//
// Основная страничка расположена в корне. Отдельные разделы динамические отображаются с помощью Alpine.js.
func NewFrontend(logger *lgr.Logger, client *mongo.Client, pub domain.Publisher) http.Handler {
	static, err := fs.Sub(static, "static")
	if err != nil {
		logger.Panicf("can't load frontend data -> %s", err)
	}

	front := Frontend{
		mux:   chi.NewRouter(),
		files: static,

		logger: logger,

		tickers: securities.NewService(
			domain.NewRepo[securities.Table](client),
			pub,
		),
		dividends: div.NewService(
			domain.NewRepo[securities.Table](client),
			domain.NewRepo[div.RawTable](client),
			pub,
		),
	}

	front.registerMainPage()
	front.registerTickersHandlers()
	front.registerDividendsHandlers()

	return &front
}

func (f Frontend) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	f.mux.ServeHTTP(writer, request)
}

func (f Frontend) registerMainPage() {
	f.mux.Handle("/{file}", http.StripPrefix("/", http.FileServer(http.FS(f.files))))

	index := template.Must(template.ParseFS(f.files, "index.html"))

	f.mux.Get("/", func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "text/html;charset=UTF-8")

		err := index.Execute(writer, nil)
		if err != nil {
			http.Error(writer, err.Error(), http.StatusInternalServerError)

			f.logger.Warnf("can't render template -> %s", err)
		}
	})
}
