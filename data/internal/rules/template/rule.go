package template

import (
	"context"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

// Rule - шаблон правила по обновлению большинства таблиц.
type Rule[R domain.Row] struct {
	name      string
	logger    *lgr.Logger
	repo      repo.ReadWrite[R]
	selector  Selector
	gateway   Gateway[R]
	validator Validator[R]
	append    bool
	timeout   time.Duration
}

// NewRule создает правило на основе шаблона.
func NewRule[R domain.Row](
	name string,
	logger *lgr.Logger,
	repo repo.ReadWrite[R],
	selector Selector,
	gateway Gateway[R],
	validator Validator[R],
	append bool,
	timeout time.Duration,
) Rule[R] {
	return Rule[R]{
		name:      name,
		logger:    logger,
		repo:      repo,
		selector:  selector,
		gateway:   gateway,
		validator: validator,
		append:    append,
		timeout:   timeout,
	}
}

// Activate шаблонное правило.
func (r Rule[R]) Activate(inbox <-chan domain.Event) <-chan domain.Event {
	out := make(chan domain.Event)

	go func() {
		r.logger.Infof("%s: started", r.name)
		defer r.logger.Infof("%s: stopped", r.name)

		defer close(out)

		var wg sync.WaitGroup
		defer wg.Wait()
		for event := range inbox {
			event := event

			wg.Add(1)

			go func() {
				defer wg.Done()

				r.handleEvent(out, event)
			}()
		}
	}()

	return out
}

func (r Rule[R]) handleEvent(out chan<- domain.Event, event domain.Event) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	var wg sync.WaitGroup
	defer wg.Wait()

	ids, err := r.selector.Select(ctx, event)
	if err != nil {
		out <- domain.NewErrorOccurred(event, err)

		return
	}

	for _, id := range ids {
		wg.Add(1)

		update := domain.NewUpdateCompleted(id, event.Date())

		go func() {
			defer wg.Done()

			if newEvent := r.handleUpdate(ctx, update); newEvent != nil {
				out <- newEvent
			}
		}()
	}
}

func (r Rule[R]) handleUpdate(ctx context.Context, update domain.UpdateCompleted) domain.Event {
	table, err := r.repo.Get(ctx, update.ID())
	if err != nil {
		return domain.NewErrorOccurred(update, err)
	}

	rows, err := r.gateway.Get(ctx, table, update.Date())
	if err != nil {
		return domain.NewErrorOccurred(update, err)
	}

	if !r.haveNewRows(rows) {
		return nil
	}

	err = r.validator(table, rows)
	if err != nil {
		return domain.NewErrorOccurred(update, err)
	}

	if r.append {
		err = r.repo.Append(ctx, domain.NewTable(update.ID(), update.Date(), rows[1:]))
	} else {
		err = r.repo.Replace(ctx, domain.NewTable(update.ID(), update.Date(), rows))
	}

	if err != nil {
		return domain.NewErrorOccurred(update, err)
	}

	return update
}

func (r Rule[R]) haveNewRows(rows []R) bool {
	if len(rows) == 0 {
		return false
	}

	if r.append && (len(rows) == 1) {
		return false
	}

	return true
}
