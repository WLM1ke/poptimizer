package main

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/api"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/pkg/app"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"net/http"
	"time"
)

type data struct {
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

func (d data) Build(logger *lgr.Logger) ([]app.ResourceCloseFunc, []app.Service) {
	mongo, err := client.MongoDB(d.MongoDB.URI)
	if err != nil {
		logger.Panicf("%s", err)
	}

	httpClient := client.NewHTTPClient(d.ISS.Connections)

	resource := []app.ResourceCloseFunc{
		func(ctx context.Context) error {
			// Драйвер MongoDB использует дефолтный клиент под капотом
			http.DefaultClient.CloseIdleConnections()

			return mongo.Disconnect(ctx)
		},
		func(ctx context.Context) error {
			httpClient.CloseIdleConnections()

			return nil
		},
	}

	db := mongo.Database(d.MongoDB.DB)

	services := []app.Service{
		api.NewHTTPServer(
			logger,
			db,
			d.Server.Addr,
			d.Server.Timeout,
		),
		bus.NewEventBus(
			logger,
			db,
			httpClient,
			d.Events.Timeout,
		),
	}

	return resource, services
}

func main() {
	var cfg data

	app.New(&cfg).Run()
}
