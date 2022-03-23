package api

import (
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/WLM1ke/poptimizer/data/pkg/server"
	"github.com/go-chi/chi"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

func NewHTTPServer(logger *lgr.Logger, db *mongo.Database, addr string, requestTimeouts time.Duration) *server.Server {
	router := chi.NewRouter()
	router.Mount("/api", jsonHandler(logger, repo.NewMongoJSON(db)))
	router.Mount("/edit", editHandler(logger))

	srv := server.NewServer(
		logger,
		addr,
		router,
		requestTimeouts,
	)

	return srv
}
