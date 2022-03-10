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
		Timeout time.Duration `envDefault:"5m"`
	}
	MongoDB struct {
		URI string `env:"URI,unset" envDefault:"mongodb://localhost:27017"`
		DB  string `envDefault:"data"`
	}
	HTTPClient struct {
		Connections int `envDefault:"20"`
	}
	Telegram struct {
		Token  string `env:"TOKEN,unset"`
		ChatID string `env:"CHAT_ID,unset"`
	}
}

func (d data) Build(logger *lgr.Logger) ([]app.ResourceCloseFunc, []app.Service) {
	mongo, err := client.MongoDB(d.MongoDB.URI)
	if err != nil {
		logger.Panicf("App: %s", err)
	}

	httpClient := client.NewHTTPClient(d.HTTPClient.Connections)

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

	telega, err := client.NewTelegram(httpClient, d.Telegram.Token, d.Telegram.ChatID)
	if err != nil {
		logger.Panicf("App: %s", err)
	}

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
			telega,
			d.Events.Timeout,
		),
	}

	return resource, services
}

func main() {
	var cfg data

	app.New(&cfg).Run()
}
