package main

import (
	"github.com/WLM1ke/poptimizer/data/internal/api"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/pkg/app"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/http"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"time"
)

type Config struct {
	App    string `envDefault:"data"`
	Server struct {
		Addr    string        `envDefault:"localhost:3000"`
		Timeout time.Duration `envDefault:"1s"`
	}
	Events struct {
		Timeout time.Duration `envDefault:"30s"`
	}
	MongoDB struct {
		URI string `env:"URI,unset" envDefault:"mongodb://localhost:27017"`
		DB  string `envDefault:"data"`
	}
	ISS struct {
		Connections int `envDefault:"20"`
	}
}

func main() {
	var cfg Config
	app.LoadConfig(&cfg)

	logger := lgr.New(cfg.App)

	services := []app.Service{
		app.NewGoroutineCounter(logger),
		http.NewServer(
			logger,
			cfg.Server.Addr,
			cfg.Server.Timeout,
			api.GetBSON(),
		),
		bus.NewEventBus(
			logger,
			client.MongoDB(cfg.MongoDB.URI, cfg.MongoDB.DB),
			client.ISS(cfg.ISS.Connections),
			cfg.Events.Timeout),
	}

	app.Run(logger, services...)
}
