// Package errors содержит правило по обработке событий-ошибок.
package errors

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

// Rule - правило обработки ошибок.
type Rule struct {
	logger *lgr.Logger
}

// New создает правило обработки событий-ошибок.
func New(logger *lgr.Logger) *Rule {
	return &Rule{logger: logger}
}

// Activate - активирует правило.
//
// Реагирует паникой на событие ошибок и не использует исходящий канал.
func (r *Rule) Activate(in <-chan domain.Event, _ chan<- domain.Event) {
	r.logger.Infof("ErrorRule: started")
	defer r.logger.Infof("ErrorRule: stopped")

	for event := range in {
		event, ok := event.(domain.ErrorOccurred)
		if ok {
			r.logger.Panicf("ErrorRule: %s", event)
		}
	}
}
