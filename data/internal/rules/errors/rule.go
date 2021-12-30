package errors

import (
	"github.com/WLM1ke/poptimizer/data/internal/rules/events"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

// Rule - правило обработки ошибок.
type Rule struct {
	Logger *lgr.Logger
}

// New создает правило обработки событий-ошибок.
func New(logger *lgr.Logger) *Rule {
	return &Rule{Logger: logger}
}

// Activate - активирует правило.
//
// Реагирует паникой на событие ошибок и не использует исходящий канал.
func (r *Rule) Activate(in <-chan events.Event, _ chan<- events.Event) {
	r.Logger.Infof("Error rule: started")
	defer r.Logger.Infof("Error rule: stopped")

	for event := range in {
		event, ok := event.(Err)
		if !ok {
			continue
		}

		r.Logger.Panicf("Rule: %v", event)
	}
}
