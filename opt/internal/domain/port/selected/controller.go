package selected

import (
	"encoding/gob"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"net/http"
)

// TickersState содержит информацию о результатах редактирования выбранных тикеров.
//
// Выбранных и не выбранных тикеров, для заданного префикса, а так же статуса изменения данных.
type TickersState struct {
	Agg    domain.Aggregate[Tickers]
	Prefix string
	Status string
}

// Selected содержит перечень выбранных тикеров.
func (s TickersState) Selected() []string {
	return s.Agg.Entity.Selected()
}

// NotSelected содержит перечень тикеров, доступных для добавления.
func (s TickersState) NotSelected() []string {
	return s.Agg.Entity.SearchNotSelected(s.Prefix)
}

// TickersController осуществляет редактирование выбранных тикеров.
type TickersController struct {
	repo domain.ReadWriteRepo[Tickers]
}

// NewTickersController создает контроллер для редактирования выбранных тикеров.
func NewTickersController(
	repo domain.ReadWriteRepo[Tickers],
) *TickersController {
	gob.Register(TickersState{})

	return &TickersController{repo: repo}
}

// Update реализует основные команды по редактированию.
//
// Команды:
// - tickers - вывод текущей информации
// - search - поиск доступных для добавления
// - save - сохранить текущие изменения
// - add/remove - добавить/удалить определенный тикер
func (c TickersController) Update(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	switch cmd := ctx.Cmd(); cmd {
	case "tickers":
		return c.tickers(ctx, state)
	case "search":
		return c.search(ctx, state)
	case "save":
		return c.save(ctx, state)
	case "add":
		return c.add(ctx, state)
	case "remove":
		return c.remove(ctx, state)
	default:
		return http.StatusInternalServerError, fmt.Errorf("incorect command %s", cmd)
	}
}

func (c TickersController) tickers(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	if state.Status != "" {
		return 0, nil
	}

	state.Agg, err = c.repo.Get(ctx, ID())
	if err != nil {
		return http.StatusInternalServerError, err
	}

	state.Status = "Not edited"

	return 0, nil
}

func (c TickersController) search(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	state.Prefix = ctx.Get("prefix")

	return 0, nil
}

func (c TickersController) save(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	if err := c.repo.Save(ctx, state.Agg); err != nil {
		return http.StatusInternalServerError, err
	}

	state.Agg, err = c.repo.Get(ctx, ID())
	if err != nil {
		return http.StatusInternalServerError, err
	}

	state.Status = "Saved successfully"

	return 0, nil
}

func (c TickersController) add(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	ticker := ctx.Get("ticker")
	if err := state.Agg.Entity.Add(ticker); err != nil {
		return http.StatusBadRequest, err
	}

	state.Status = "Edited"

	return 0, nil
}

func (c TickersController) remove(ctx domain.CtrlCtx, state *TickersState) (code int, err error) {
	ticker := ctx.Get("ticker")
	if err := state.Agg.Entity.Remove(ticker); err != nil {
		return http.StatusBadRequest, err
	}

	state.Status = "Edited"

	return 0, nil
}
