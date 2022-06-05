package front

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/alexedwards/scs/v2"
	"github.com/go-chi/chi"
	"html/template"
	"net/http"
	"net/url"
	"path"
)

const _stateKey = `state`

// Context реализует контекст для обработчиков редактирования доменных сущностей.
type Context struct {
	context.Context
	PostForm url.Values
}

// Get получает дополнительные параметры команд для обработчика.
func (c Context) Get(key string) string {
	value := chi.URLParamFromCtx(c.Context, key)
	if value != "" {
		return value
	}

	return c.PostForm.Get(key)
}

// Handler представляет универсальный обработчик для группы элементов страницы.
//
// Перенаправляет http-запросы к обработчикам доменных объектов осуществляет рендеринг на основе полученного состояния,
// при этом действует на основе следующих основных соглашений:
// - последний сегмент пути запроса является командой к обработчику
// - все параметры команд должны содержаться в теле запроса, а не в URL
// - если команда совпадает с именем страницы обработчика, то для конечного рендеринга используется шаблон "index", а
// для остальных команд "update"
type handler[S domain.State] struct {
	logger *lgr.Logger

	smg  *scs.SessionManager
	ctrl domain.Controller[S]

	tmpl *template.Template
	page string
}

func (h handler[S]) ServeHTTP(writer http.ResponseWriter, request *http.Request) {
	if err := request.ParseForm(); err != nil {
		http.Error(writer, fmt.Sprintf("can't parse form"), http.StatusBadRequest)

		return
	}

	ctx := Context{
		Context:  request.Context(),
		PostForm: request.PostForm,
	}

	cmd := path.Base(request.URL.Path)

	state, err := h.prepareState(request)
	if err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)
	}

	if code, err := h.ctrl.Update(ctx, cmd, &state); err != nil {
		http.Error(writer, err.Error(), code)

		return
	}

	h.smg.Put(request.Context(), _stateKey, state)

	tmpl := "update"
	if cmd == h.page {
		tmpl = "index"
	}

	h.execTemplate(writer, tmpl, state)
}

func (h handler[S]) prepareState(request *http.Request) (S, error) {
	if h.smg.Exists(request.Context(), _stateKey) {
		state, ok := h.smg.Get(request.Context(), _stateKey).(S)
		if !ok {
			return state, fmt.Errorf("can't load page state")
		}

		return state, nil
	}

	var state S

	return state, nil
}

func (h handler[S]) execTemplate(w http.ResponseWriter, tmpl string, state S) {
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	err := h.tmpl.ExecuteTemplate(w, tmpl, state)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)

		h.logger.Warnf("can't render template %s -> %s", tmpl, err)
	}
}
