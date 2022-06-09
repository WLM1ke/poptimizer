package app

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

// ErrorsHandler логирует и посылает в телеграм события с ошибками.
type ErrorsHandler struct {
	logger   *lgr.Logger
	telegram *clients.Telegram
}

// Match выбирает события, содержащие ошибки.
func (e ErrorsHandler) Match(event domain.Event) bool {
	if _, ok := event.Data.(error); ok {
		return true
	}

	return false
}

func (e ErrorsHandler) String() string {
	return `Filter("error")`
}

// NewErrorsHandler создает новый обработчик событий с ошибками.
func NewErrorsHandler(logger *lgr.Logger, telegram *clients.Telegram) *ErrorsHandler {
	return &ErrorsHandler{
		logger:   logger,
		telegram: telegram,
	}
}

// Handle перехватывает события с ошибками, логирует и посылает их в телеграм.
func (e ErrorsHandler) Handle(ctx context.Context, event domain.Event) {
	err, ok := event.Data.(error)
	if !ok {
		err = fmt.Errorf("incorrect error %s routing", event)
	}

	e.logger.Warnf("%s", err)

	ctx, cancel := context.WithTimeout(ctx, _errorTimeout)
	defer cancel()

	if err = e.telegram.Send(ctx, err.Error()); err != nil {
		e.logger.Warnf("can't send notification -> %s", err)
	}
}
