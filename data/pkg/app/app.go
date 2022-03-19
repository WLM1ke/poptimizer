package app

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.uber.org/goleak"
)

// Service представляет компоненту приложения.
type Service interface {
	// Run запускает службу в блокирующем режиме с отменой по завершению контекста.
	Run(context.Context) error
}

// ResourceCloseFunc - функция корректно высвобождающая используемый ресурс приложения.
type ResourceCloseFunc func(ctx context.Context) error

// Config конфигурация приложения.
//
// Приложение во время запуска загружает конфигурацию используя теги структуры.
type Config interface {
	// Build - инициализирует необходимые для работы приложения ресурсы и службы.
	Build(logger *lgr.Logger) ([]ResourceCloseFunc, []Service)
}

// App представляет приложение.
type App struct {
	logger *lgr.Logger
	config Config

	code int

	services  []Service
	resources []ResourceCloseFunc
}

// New создает новое приложение на основе конфигурации.
//
// Ресурсы и службы не инициализируются в момент создания.
func New(config Config) *App {
	return &App{
		config: config,
	}
}

// Run запускает приложение.
//
// Загружает конфигурацию, инициализирует ресурсы и службы и запускает их. Работа служб завершается в случае ошибки в
// работе одной из них или поступления системного сигнала, после чего высвобождаются используемые ресурсы.
func (a *App) Run() {
	defer func() {
		a.logger.Infof("App: stopped with exit code %d", a.code)
		os.Exit(a.code)
	}()

	a.createLogger()
	a.loadConfig()

	a.logger.Infof("App: starting")

	a.resources, a.services = a.config.Build(a.logger)
	a.logger.Infof("App: %d resource(s) acquired", len(a.resources))

	a.runServices()
	a.closeResources()

	if a.code == 0 {
		a.checkLeaks()
	}
}

func (a *App) checkLeaks() {
	if err := goleak.Find(); err != nil {
		a.code = 1
		a.logger.Warnf("App: %v", err)
	}
}

func shortType(value interface{}) string {
	parts := strings.Split(fmt.Sprintf("%T", value), ".")

	return parts[len(parts)-1]
}
