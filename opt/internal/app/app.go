package app

import (
	"context"
	"net/http"
	"sync"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/cpi"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/index"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/trading"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/update"
	"github.com/WLM1ke/poptimizer/opt/internal/repository"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/caarlos0/env/v6"
)

type config struct {
	App struct {
		GoroutineInterval time.Duration `envDefault:"1h"`
	}
	Server struct {
		Addr           string        `envDefault:"localhost:10000"`
		RespondTimeout time.Duration `envDefault:"1s"`
	}
	HTTPClient struct {
		Connections int `envDefault:"20"`
	}
	MongoDB struct {
		URI string `env:"URI,unset" envDefault:"mongodb://localhost:27017"`
	}
	Telegram struct {
		Token  string `env:"TOKEN,unset"`
		ChatID string `env:"CHAT_ID,unset"`
	}
}

// App осуществляет инициализацию и запуск всех сервисов приложения.
type App struct {
	logger lgr.Logger
}

// New создает приложение.
func New(logger lgr.Logger) *App {
	return &App{logger: logger}
}

// Run запускает приложение.
func (a App) Run(ctx context.Context) {
	cfg := a.loadConfig()

	httpClient := clients.NewHTTPClient(cfg.HTTPClient.Connections)
	defer httpClient.CloseIdleConnections()

	telega, err := clients.NewTelegram(httpClient, cfg.Telegram.Token, cfg.Telegram.ChatID)
	if err != nil {
		a.logger.Panicf("can't create telegram client -> %s", err)
	}

	a.logger = logger{
		logger: a.logger,
		telega: telega,
	}

	mongoClient, err := clients.NewMongoClient(cfg.MongoDB.URI)
	if err != nil {
		a.logger.Panicf("can't create MongoDB client -> %s", err)
	}

	defer func() {
		err := mongoClient.Disconnect(context.Background())
		if err != nil {
			a.logger.Panicf("can't stop MongoDB Client -> %s", err)
		}

		// Драйвер MongoDB использует дефолтный клиент под капотом
		http.DefaultClient.CloseIdleConnections()
	}()

	iss := gomoex.NewISSClient(httpClient)

	dataSrv, err := update.NewService(
		a.logger.WithPrefix("UpdateSrv"),
		trading.NewService(repository.NewMongo[trading.Date](mongoClient), iss),
		cpi.NewService(a.logger.WithPrefix("CPI"), repository.NewMongo[cpi.Table](mongoClient), httpClient),
		index.NewService(a.logger.WithPrefix("Indexes"), repository.NewMongo[index.Table](mongoClient), iss),
		securities.NewService(a.logger.WithPrefix("Securities"), repository.NewMongo[securities.Table](mongoClient), iss),
		quote.NewService(a.logger.WithPrefix("Quotes"), repository.NewMongo[quote.Table](mongoClient), iss),
		raw.NewStatusService(a.logger.WithPrefix("Status"), repository.NewMongo[raw.StatusTable](mongoClient), httpClient),
		raw.NewReestryService(a.logger.WithPrefix("CloseReestry"), repository.NewMongo[raw.Table](mongoClient), httpClient),
		raw.NewNASDAQService(a.logger.WithPrefix("NASDAQ"), repository.NewMongo[raw.Table](mongoClient), httpClient),
	)
	if err != nil {
		a.logger.Panicf("can't create data update service -> %s", err)
	}

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	waitGroup.Add(1)

	go func() {
		defer waitGroup.Done()

		goroutineCounter(ctx, a.logger)
	}()

	if err := dataSrv.Run(ctx); err != nil {
		a.logger.Panicf("error while stopping data update service -> %s", err)
	}
}

func (a App) loadConfig() (cfg config) {
	if err := env.Parse(&cfg); err != nil {
		a.logger.Panicf("can't load config -> %s", err)
	}

	a.logger.Infof("config loaded")

	return cfg
}
