package main

import (
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/api"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/pkg/app"
	"github.com/WLM1ke/poptimizer/data/pkg/http"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_appName = "data"

	_serverAddr    = "localhost:3000"
	_serverTimeout = time.Second

	_clientTimeout = 30 * time.Second
	_mongoURI      = "mongodb://localhost:27017"
	_mongoDB       = "data_new"

	_issConn = 20
)

func main() {
	logger := lgr.New(_appName)

	services := []app.Service{
		app.NewGoroutineCounter(logger),
		http.NewServer(
			logger,
			_serverAddr,
			_serverTimeout,
			api.GetBSON(),
		),
		bus.NewEventBus(
			logger,
			client.MongoDB(_mongoURI, _mongoDB),
			client.ISS(_issConn),
			_clientTimeout),
	}

	app.Run(logger, services...)
}
