package handlers

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/handlers/edit"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/services"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/WLM1ke/poptimizer/data/pkg/server"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
)

// NewHTTPServer создает сервер по получению и обновлению данных.
//
// /api/{group}/{ticker} - получение данных по входящему в группу тикеру.
// /edit/{ticker} - frontend для добавления данных по дивидендам.
func NewHTTPServer(
	logger *lgr.Logger,
	db *mongo.Database,
	service *services.RawDivUpdate,
	addr string,
	requestTimeouts time.Duration,
) *server.Server {
	router := chi.NewRouter()
	router.Mount("/api", newJSONHandler(logger, repo.NewMongoJSON(db)))
	router.Mount("/edit", edit.NewEditHandler(logger, service))

	srv := server.NewServer(
		logger,
		addr,
		router,
		requestTimeouts,
	)

	return srv
}
