package securities

import (
	"encoding/gob"
	"fmt"
	"net/http"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// State содержит информацию о результатах редактирования выбранных тикеров.
//
// Выбранных и не выбранных тикеров, для заданного префикса, а так же статуса изменения данных.
type State struct {
	Agg    domain.Aggregate[Table]
	Prefix string
	Status string
}

// Selected содержит перечень выбранных тикеров.
func (s State) Selected() []string {
	return s.Agg.Entity.Selected()
}

// NotSelected содержит перечень тикеров, доступных для добавления.
func (s State) NotSelected() []string {
	return s.Agg.Entity.NotSelected(s.Prefix)
}

// Controller осуществляет редактирование выбранных тикеров.
type Controller struct {
	repo domain.ReadWriteRepo[Table]
	pub  domain.Publisher
}

// NewController создает контроллер для редактирования выбранных тикеров.
func NewController(
	repo domain.ReadWriteRepo[Table],
	pub domain.Publisher,
) *Controller {
	gob.Register(State{})

	return &Controller{repo: repo, pub: pub}
}

// Update реализует основные команды по редактированию.
//
// Команды:
// - tickers - вывод текущей информации
// - search - поиск доступных для добавления
// - save - сохранить текущие изменения
// - add/remove - добавить/удалить определенный тикер.
func (c Controller) Update(ctx domain.CtrlCtx, cmd string, state *State) (code int, err error) {
	switch cmd {
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
		return http.StatusInternalServerError, fmt.Errorf("incorrect command %s", cmd)
	}
}

func (c Controller) tickers(ctx domain.CtrlCtx, state *State) (code int, err error) {
	if state.Status != "" {
		return http.StatusOK, nil
	}

	state.Agg, err = c.repo.Get(ctx, ID())
	if err != nil {
		return http.StatusInternalServerError, err
	}

	state.Status = "Not edited"

	return http.StatusOK, nil
}

func (c Controller) search(ctx domain.CtrlCtx, state *State) (code int, err error) {
	state.Prefix = ctx.Get("prefix")

	return http.StatusOK, nil
}

func (c Controller) save(ctx domain.CtrlCtx, state *State) (code int, err error) {
	if err := c.repo.Save(ctx, state.Agg); err != nil {
		return http.StatusInternalServerError, err
	}

	c.pub.Publish(domain.Event{
		QualifiedID: ID(),
		Timestamp:   state.Agg.Timestamp,
		Data:        state.Agg.Entity,
	})

	state.Agg, err = c.repo.Get(ctx, ID())
	if err != nil {
		return http.StatusInternalServerError, err
	}

	state.Status = "Saved successfully"

	return http.StatusOK, nil
}

func (c Controller) add(ctx domain.CtrlCtx, state *State) (code int, err error) {
	ticker := ctx.Get("ticker")
	if !state.Agg.Entity.Select(ticker) {
		return http.StatusBadRequest, fmt.Errorf("wrong ticker")
	}

	state.Status = "Edited"

	return http.StatusOK, nil
}

func (c Controller) remove(ctx domain.CtrlCtx, state *State) (code int, err error) {
	ticker := ctx.Get("ticker")
	if !state.Agg.Entity.Unselect(ticker) {
		return http.StatusBadRequest, fmt.Errorf("wrong ticker")
	}

	state.Status = "Edited"

	return http.StatusOK, nil
}
