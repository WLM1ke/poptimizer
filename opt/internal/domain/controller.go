package domain

import "context"

// State представляет доменный агрегат и информацию по взаимодействию с ним, для визуализации пользователю.
type State any

// CtrlCtx представляет контекст контролера, который дополнительно несет информацию о параметрах.
type CtrlCtx interface {
	context.Context
	Get(key string) string
}

// Controller обеспечивает обработку запросов в рамках MVC.
type Controller[S State] interface {
	// Update меняет состояние доменного объекта на основе команды и ее параметров из контекста.
	Update(ctx CtrlCtx, cmd string, state *S) (code int, err error)
}
