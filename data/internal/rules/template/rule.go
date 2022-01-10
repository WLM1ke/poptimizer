package template

import (
	"context"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"sync"
)

type Rule[R any] struct {
	repo    repo.ReadWrite[R]
	selector Selector
	gateway Gateway[R]
	validator Validator[R]
	append  bool
	ctxFunc eventCtxFunc
}

func NewRule[R any](
	repo repo.ReadWrite[R],
	selector Selector,
	gateway Gateway[R],
	validator Validator[R],
	append bool,
	ctxFunc eventCtxFunc,
	) *Rule[R] {
	return &Rule[R]{
		repo: repo,
		selector: selector,
		gateway: gateway,
		validator: validator,
		append: append,
		ctxFunc: ctxFunc,
	}
}



func (r Rule[R]) Activate(in <-chan domain.Event, out chan<- domain.Event) {
	var wg sync.WaitGroup
	defer wg.Wait()

	for event := range in {
		wg.Add(1)

		event := event

		go func() {
			defer wg.Done()

			r.handleEvent(out, event)
		}()
	}

}

func (r Rule[R]) handleEvent(out chan<- domain.Event, event domain.Event) {
	var wg sync.WaitGroup
	defer wg.Wait()

	ctx, cancel := r.ctxFunc()
	defer cancel()

	ids, err := r.selector(ctx, event)
	if err != nil {
		out <- domain.NewErrorOccurred(event, err)

		return
	}

	for _, id := range ids {
		id := id

		wg.Add(1)

		go func() {
			defer wg.Done()

			if newEvent := r.updateTableToVer(ctx, domain.NewVersion(id, event.Date())); newEvent != nil {
				out <- newEvent
			}

		}()
	}
}

func (r Rule[R]) updateTableToVer(ctx context.Context, ver domain.Version) domain.Event {
	ctx, cancel := r.ctxFunc()
	defer cancel()

	table, err := r.repo.Get(ctx, ver)
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	rows, err := r.gateway(ctx, table, ver.Date())
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	err = r.validator(table, rows)
	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	if r.append {
		table = domain.Table[R]{ver, rows[1:]}
		err = r.repo.Append(ctx, table)
	} else {
		table = domain.Table[R]{ver, rows}
		err = r.repo.Replace(ctx, table)
	}

	if err != nil {
		return domain.NewErrorOccurred(ver, err)
	}

	return domain.NewUpdateCompleted(ver)
}
