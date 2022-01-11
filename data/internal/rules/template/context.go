package template

import (
	"context"
	"time"
)

// EventCtxFunc - функция, создающие контексты для обработки отдельных событий.
type EventCtxFunc func() (context.Context, context.CancelFunc)

func EventCtxFuncWithTimeout(timeout time.Duration) EventCtxFunc {
	return func() (context.Context, context.CancelFunc) {
		return context.WithTimeout(context.Background(), timeout)
	}
}
