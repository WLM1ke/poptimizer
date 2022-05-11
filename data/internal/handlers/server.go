package handlers

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/handlers/frontend"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/WLM1ke/poptimizer/data/pkg/server"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

// NewHTTPServer создает сервер по получению и обновлению данных.
//
// /api/{group}/{ticker} - получение данных по входящему в группу тикеру.
//
// /edit/div/{ticker} - frontend для добавления данных по дивидендам.
//
// /edit/port/tickers - frontend для редактирования перечня тикеров в составе портфеля, для которых будет отслеживаться
// появление новых дивидендов.
func NewHTTPServer(
	logger *lgr.Logger,
	database *mongo.Database,
	eventBus *bus.EventBus,
	addr string,
	requestTimeouts time.Duration,
) *server.Server {
	router := chi.NewRouter()
	router.Mount("/api", newJSONHandler(logger, repo.NewMongoJSON(database)))

	router.Mount(
		"/",
		frontend.NewFrontend(logger, database, eventBus),
	)

	return server.NewServer(
		logger,
		addr,
		router,
		requestTimeouts,
	)
}
