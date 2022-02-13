// Package errors содержит правило по обработке событий-ошибок.
package errors

import (
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"time"
)

// Rule - правило обработки ошибок.
type Rule struct {
	logger   *lgr.Logger
	telegram *client.Telegram
	ctxFunc  template.EventCtxFunc
}

// New создает правило обработки событий-ошибок.
func New(logger *lgr.Logger, telegram *client.Telegram, timeout time.Duration) *Rule {
	return &Rule{logger: logger, telegram: telegram, ctxFunc: template.EventCtxFuncWithTimeout(timeout)}
}

// Activate - активирует правило.
//
// Пишет в лог предупреждения и посылает сообщения в Telegram.
func (r *Rule) Activate(in <-chan domain.Event, _ chan<- domain.Event) {
	r.logger.Infof("ErrorRule: started")
	defer r.logger.Infof("ErrorRule: stopped")

	for event := range in {
		event, ok := event.(domain.ErrorOccurred)
		if ok {
			r.process(event)
		}
	}
}

func (r *Rule) process(event domain.ErrorOccurred) {
	r.logger.Warnf("ErrorRule: %s", event)

	ctx, cancel := r.ctxFunc()
	defer cancel()

	err := r.telegram.Send(ctx, fmt.Sprint(event))
	if err != nil {
		r.logger.Warnf("ErrorRule: can't send to telegram %s -> %s", event, err)
	}
}
