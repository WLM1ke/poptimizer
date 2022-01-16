package app

import "context"

func (a *App) closeResources() {
	closeCtx := context.Background()
	for _, resource := range a.resources {
		if err := resource(closeCtx); err != nil {
			a.code = 1
			a.logger.Warnf("App: error during closing resource %s -> %s", shortType(resource), err)
		}
	}

	a.logger.Infof("App: %d resource(s) is closed", len(a.resources))
}
