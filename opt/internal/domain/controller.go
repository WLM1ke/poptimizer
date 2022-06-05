package domain

import "context"

type State any

// CtrlCtx представляет контекст контролера, который дополнительно несет информацию о команде и ее параметрах.
type CtrlCtx interface {
	context.Context
	Cmd() string
	Get(key string) string
}

// Controller обеспечивает обработку запросов в рамках MVC.
type Controller[S State] interface {
	// Update меняет состояние доменного объекта на основе команды и ее параметров из контекста.
	Update(ctx CtrlCtx, state *S) (code int, err error)
}
