package app

import "github.com/WLM1ke/poptimizer/data/pkg/lgr"

func (a *App) createLogger() {
	a.logger = lgr.New(shortType(a.config))
	a.logger.Infof("App: logger created")
}
