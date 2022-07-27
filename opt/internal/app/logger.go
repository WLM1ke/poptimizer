package app

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _sendTimeout = time.Minute

type appLgr struct {
	logger lgr.Logger
	telega *clients.Telegram
}

func (l appLgr) WithPrefix(prefix string) lgr.Logger {
	return appLgr{
		logger: l.logger.WithPrefix(prefix),
		telega: l.telega,
	}
}

func (l appLgr) Infof(format string, args ...any) {
	l.logger.Infof(format, args...)
}

func (l appLgr) Warnf(format string, args ...any) {
	ctx, cancel := context.WithTimeout(context.Background(), _sendTimeout)
	defer cancel()

	err := l.telega.Send(ctx, fmt.Sprintf(format, args...))
	if err != nil {
		l.logger.Warnf("can't send notification -> %s", err)
	}

	l.logger.Warnf(format, args...)
}
