package template

import (
	"context"
	"time"
)

// eventCtxFunc - функция, создающие контексты для обработки отбельных событий.
type eventCtxFunc func() (context.Context, context.CancelFunc)

func eventCtxWithTimeout(ctx context.Context, timeout time.Duration) eventCtxFunc {
	return func() (context.Context, context.CancelFunc) {
		return context.WithTimeout(ctx, timeout)
	}
}
