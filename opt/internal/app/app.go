package app

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"sync"
	"syscall"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/api"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/cpi"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/div"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/index"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/trading"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/usd"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio/port"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/update"
	"github.com/WLM1ke/poptimizer/opt/internal/repository"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/WLM1ke/poptimizer/opt/pkg/servers"
	"github.com/WLM1ke/poptimizer/opt/web"
	"github.com/caarlos0/env/v6"
	"go.mongodb.org/mongo-driver/mongo"
	"go.uber.org/goleak"
)

// App осуществляет инициализацию и запуск всех сервисов приложения.
type App struct {
	GoroutineInterval time.Duration `envDefault:"1h"`
	Server            struct {
		Addr           string        `envDefault:"localhost:10000"`
		RespondTimeout time.Duration `envDefault:"2s"`
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

	logger lgr.Logger
	http   *http.Client
	mongo  *mongo.Client

	resourcesClosers []func()

	services []func(ctx context.Context)
}

// Run запускает приложение.
func (a *App) Run() {
	var err error

	defer func() {
		a.atExit(err)
	}()

	if err = a.initResources(); err != nil {
		return
	}

	if err = a.prepareServices(); err != nil {
		return
	}

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	ctx := a.appCtx()

	for _, s := range a.services {
		srv := s

		waitGroup.Add(1)

		go func() {
			defer waitGroup.Done()

			srv(ctx)
		}()
	}
}

func (a *App) atExit(err error) {
	for _, closeFunc := range a.resourcesClosers {
		closeFunc()
	}

	if r := recover(); r != nil {
		a.logger.Warnf("stopped with exit code 1 -> %s", r)
		os.Exit(1)
	}

	if err != nil {
		a.logger.Warnf("stopped with exit code 1 -> %s", err)
		os.Exit(1)
	}

	if err := goleak.Find(); err != nil {
		a.logger.Warnf("stopped with exit code 1 -> found leaked goroutines %s", err)
		os.Exit(1)
	}

	a.logger.Infof("stopped with exit code 0")
	os.Exit(0)
}

func (a *App) initResources() error {
	a.logger = lgr.New("App")

	if err := env.Parse(a); err != nil {
		return fmt.Errorf("can't load config -> %w", err)
	}

	a.logger.Infof("config loaded")

	a.http = clients.NewHTTPClient(a.HTTPClient.Connections)
	a.resourcesClosers = append(a.resourcesClosers, a.http.CloseIdleConnections)

	telega, err := clients.NewTelegram(a.http, a.Telegram.Token, a.Telegram.ChatID)
	if err != nil {
		return fmt.Errorf("can't create telegram client -> %w", err)
	}

	a.logger = appLgr{
		logger: a.logger,
		telega: telega,
	}

	a.mongo, err = clients.NewMongoClient(a.MongoDB.URI)
	if err != nil {
		return fmt.Errorf("can't create MongoDB client -> %w", err)
	}

	a.resourcesClosers = append(a.resourcesClosers, func() {
		err := a.mongo.Disconnect(context.Background())
		if err != nil {
			a.logger.Warnf("can't stop MongoDB Client -> %s", err)
		}

		// Драйвер MongoDB использует дефолтный клиент под капотом
		http.DefaultClient.CloseIdleConnections()
	})

	return nil
}

func (a *App) prepareServices() error {
	dataSrv, err := a.prepareUpdateSrv()
	if err != nil {
		return err
	}

	server, err := a.prepareServer()
	if err != nil {
		return fmt.Errorf("can't create server -> %w", err)
	}

	a.services = append(a.services, server.Run, dataSrv.Run, a.goroutineCounter)

	return nil
}

func (a *App) prepareUpdateSrv() (*update.Service, error) {
	iss := gomoex.NewISSClient(a.http)

	rawRepo := repository.NewMongo[raw.Table](a.mongo)
	secRepo := repository.NewMongo[securities.Table](a.mongo)
	quoteRepo := repository.NewMongo[quote.Table](a.mongo)

	service, err := update.NewService(
		a.logger.WithPrefix("UpdateSrv"),
		repository.NewBackupRestoreService(a.MongoDB.URI, a.mongo),
		trading.NewService(repository.NewMongo[trading.Date](a.mongo), iss),
		cpi.NewService(a.logger.WithPrefix("CPI"), repository.NewMongo[cpi.Table](a.mongo), a.http),
		index.NewService(a.logger.WithPrefix("Indexes"), repository.NewMongo[index.Table](a.mongo), iss),
		securities.NewService(a.logger.WithPrefix("Securities"), secRepo, iss),
		usd.NewService(a.logger.WithPrefix("USD"), repository.NewMongo[usd.Table](a.mongo), iss),
		div.NewService(a.logger.WithPrefix("Dividends"), repository.NewMongo[div.Table](a.mongo), rawRepo),
		quote.NewService(a.logger.WithPrefix("Quotes"), quoteRepo, iss),
		raw.NewStatusService(
			a.logger.WithPrefix("Status"),
			repository.NewMongo[raw.StatusTable](a.mongo),
			a.http,
		),
		raw.NewReestryService(a.logger.WithPrefix("CloseReestry"), rawRepo, a.http),
		raw.NewNASDAQService(a.logger.WithPrefix("NASDAQ"), rawRepo, a.http),
		raw.NewCheckRawService(a.logger.WithPrefix("CheckRaw"), rawRepo),
		port.NewService(
			a.logger.WithPrefix("Portfolio"),
			repository.NewMongo[port.Portfolio](a.mongo),
			secRepo,
			quoteRepo,
		),
	)
	if err != nil {
		return nil, fmt.Errorf("can't create update service -> %w", err)
	}

	return service, nil
}

func (a *App) prepareServer() (*servers.Server, error) {
	viewer := repository.NewMongoJSONViewer(a.mongo)

	spa, err := web.GetSPAFiles()
	if err != nil {
		return nil, fmt.Errorf("can't load SPA files -> %w", err)
	}

	secRepo := repository.NewMongo[securities.Table](a.mongo)
	backupSrv := repository.NewBackupRestoreService(a.MongoDB.URI, a.mongo)
	portRepo := repository.NewMongo[port.Portfolio](a.mongo)

	handler := api.NewHandler(
		viewer,
		spa,
		securities.NewEditService(
			a.logger.WithPrefix("SecEdit"),
			secRepo,
			backupSrv,
		),
		raw.NewEditRawService(
			a.logger.WithPrefix("RawEdit"),
			secRepo,
			repository.NewMongo[raw.Table](a.mongo),
			backupSrv,
		),
		port.NewAccEditService(
			portRepo,
		),
		port.NewViewPortfolioService(
			portRepo,
		),
	)

	return servers.NewHTTPServer(a.logger, a.Server.Addr, handler, a.Server.RespondTimeout), nil
}

func (a *App) goroutineCounter(ctx context.Context) {
	ticker := time.NewTicker(a.GoroutineInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			a.logger.Infof("%d goroutines are running", runtime.NumGoroutine())
		case <-ctx.Done():
			return
		}
	}
}

func (a *App) appCtx() context.Context {
	ctx, appCancel := context.WithCancel(context.Background())

	go func() {
		defer appCancel()

		ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
		defer cancel()

		<-ctx.Done()

		a.logger.Infof("shutdown signal received")
	}()

	return ctx
}
