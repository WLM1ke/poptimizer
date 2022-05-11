package app

import (
	"github.com/caarlos0/env/v6"
)

func (a *App) loadConfig() {
	if err := env.Parse(a.config); err != nil {
		a.code = 1
		a.logger.Panicf("can't load config -> %s", err)
	}

	a.logger.Infof("App: config loaded")
}
