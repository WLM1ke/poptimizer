package app

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _sendTimeout = time.Minute

type logger struct {
	logger lgr.Logger
	telega *clients.Telegram
}

func (l logger) WithPrefix(prefix string) lgr.Logger {
	return logger{
		logger: l.logger.WithPrefix(prefix),
		telega: l.telega,
	}
}

func (l logger) Infof(format string, args ...any) {
	l.logger.Infof(format, args...)
}

func (l logger) Warnf(format string, args ...any) {
	ctx, cancel := context.WithTimeout(context.Background(), _sendTimeout)
	defer cancel()

	err := l.telega.Send(ctx, fmt.Sprintf(format, args...))
	if err != nil {
		l.logger.Warnf("can't send notification -> %s", err)
	}

	l.logger.Warnf(format, args...)
}

func (l logger) Panicf(format string, args ...any) {
	ctx, cancel := context.WithTimeout(context.Background(), _sendTimeout)
	defer cancel()

	err := l.telega.Send(ctx, fmt.Sprintf(format, args...))
	if err != nil {
		l.logger.Warnf("can't send notification -> %s", err)
	}

	l.logger.Panicf(format, args...)
}
