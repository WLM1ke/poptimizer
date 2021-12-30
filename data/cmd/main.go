package main

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/handler"
	"github.com/WLM1ke/poptimizer/data/pkg/app"
	"github.com/WLM1ke/poptimizer/data/pkg/http"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_app  = "data"
	_addr = "localhost:3000"
)

func main() {
	logger := lgr.New(_app)

	services := []app.Service{
		app.NewGoroutineCounter(logger),
		http.NewServer(
			logger,
			_addr,
			time.Second,
			handler.GetBSON(),
		),
		bus.NewEventBus(logger),
	}

	app.Run(logger, services...)
}
