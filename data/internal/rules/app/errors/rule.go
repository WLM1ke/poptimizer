// Package errors содержит правило по обработке событий-ошибок.
package errors

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

// Rule - правило обработки ошибок.
type Rule struct {
	logger   *lgr.Logger
	telegram *client.Telegram
	timeout  time.Duration
}

// New создает правило обработки событий-ошибок.
func New(logger *lgr.Logger, telegram *client.Telegram, timeout time.Duration) *Rule {
	return &Rule{
		logger:   logger,
		telegram: telegram,
		timeout:  timeout,
	}
}

// Activate - активирует правило.
//
// Пишет в лог предупреждения и посылает сообщения в Telegram, и ничего не пишет в выходящий канал.
func (r *Rule) Activate(inbox <-chan domain.Event) <-chan domain.Event {
	out := make(chan domain.Event)

	go func() {
		r.logger.Infof("ErrorRule: started")
		defer r.logger.Infof("ErrorRule: stopped")

		defer close(out)

		for event := range inbox {
			event, ok := event.(domain.ErrorOccurred)
			if ok {
				r.process(event)
			}
		}
	}()

	return out
}

func (r *Rule) process(event domain.ErrorOccurred) {
	r.logger.Warnf("ErrorRule: %s", event)

	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	err := r.telegram.Send(ctx, fmt.Sprint(event))
	if err != nil {
		r.logger.Warnf("ErrorRule: can't send to telegram %s -> %s", event, err)
	}
}
