package main

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/handlers"
	"github.com/WLM1ke/poptimizer/data/internal/rules/app/backup"
	"github.com/WLM1ke/poptimizer/data/pkg/app"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
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

			err := mongo.Disconnect(ctx)
			if err != nil {
				return fmt.Errorf("can't stop DefaultClient -> %w", err)
			}

			return nil
		},
		func(ctx context.Context) error {
			httpClient.CloseIdleConnections()

			return nil
		},
	}

	database := mongo.Database(d.MongoDB.DB)

	telega, err := client.NewTelegram(httpClient, d.Telegram.Token, d.Telegram.ChatID)
	if err != nil {
		logger.Panicf("App: %s", err)
	}

	eventBus := bus.NewEventBus(
		logger,
		database,
		backup.CreateCMD(d.MongoDB.URI, d.MongoDB.DB),
		httpClient,
		telega,
	)

	return resource, []app.Service{
		eventBus,
		handlers.NewHTTPServer(
			logger,
			database,
			eventBus,
			d.Server.Addr,
			d.Server.Timeout,
		),
	}
}

func main() {
	var cfg data

	app.New(&cfg).Run()
}
