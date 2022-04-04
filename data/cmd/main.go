package main

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/handlers"
	"github.com/WLM1ke/poptimizer/data/internal/rules/backup"
	"github.com/WLM1ke/poptimizer/data/internal/services"
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
	mongo, err := client.NewMongoDB(d.MongoDB.URI)
	if err != nil {
		logger.Panicf("App: %s", err)
	}

	httpClient := client.NewHTTPClient(d.HTTPClient.Connections)

	resource := []app.ResourceCloseFunc{
		func(ctx context.Context) error {
			// Драйвер MongoDB использует дефолтный клиент под капотом
			http.DefaultClient.CloseIdleConnections()

			return mongo.Disconnect(ctx) //nolint:wrapcheck
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

	eventBus := bus.NewEventBus(
		logger,
		db,
		backup.CreateCMD(d.MongoDB.URI, d.MongoDB.DB),
		httpClient,
		telega,
	)

	rawDiv := services.NewRawDivUpdate(logger, db, eventBus)

	return resource, []app.Service{
		eventBus,
		rawDiv,
		handlers.NewHTTPServer(
			logger,
			db,
			rawDiv,
			d.Server.Addr,
			d.Server.Timeout,
		),
	}
}

func main() {
	var cfg data

	app.New(&cfg).Run()
}
