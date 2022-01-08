package api

import (
	"fmt"
	"net/http"

	"github.com/go-chi/chi"
)

// GetBSON основной обработчик отдающий данные в формате BSON для http-сервера.
func GetBSON() http.Handler {
	router := chi.NewRouter()
	router.Get("/{group}/{name}", func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		deadline, _ := ctx.Deadline()

		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		if _, err := fmt.Fprint(w, deadline); err != nil {
			panic(err)
		}
	})

	return router
}
