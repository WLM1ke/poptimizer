package app

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

type ErrorsHandler struct {
	domain.Filter

	logger   *lgr.Logger
	telegram *clients.Telegram
}

func NewErrorsHandler(logger *lgr.Logger, telegram *clients.Telegram) *ErrorsHandler {
	return &ErrorsHandler{
		Filter:   domain.Filter{Err: true},
		logger:   logger,
		telegram: telegram,
	}
}

func (e ErrorsHandler) Handle(ctx context.Context, event domain.Event) {
	err, ok := event.Data.(error)
	if !ok {
		err = fmt.Errorf("incorrect error %s routing", event)
	}

	e.logger.Warnf("can't handle event -> %s", err)

	ctx, cancel := context.WithTimeout(context.Background(), _errorTimeout)
	defer cancel()

	if err = e.telegram.Send(ctx, err.Error()); err != nil {
		e.logger.Warnf("can't send notification -> %s", err)
	}
}
