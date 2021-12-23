package http

import (
	"github.com/WLM1ke/poptimizer/data/pkg/log"
	"github.com/go-chi/chi/middleware"
	"net/http"
	"time"
)

// Middleware реализует логирование запроса.
func Middleware(logger *log.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		handlerFunc := func(writer http.ResponseWriter, request *http.Request) {
			writerWithStats := middleware.NewWrapResponseWriter(writer, request.ProtoMajor)
			start := time.Now()

			defer func() {
				logger.Infof(
					"Request: method - %s, uri - %s, status - %d, size - %d, time - %s",
					request.Method,
					request.RequestURI,
					writerWithStats.Status(),
					writerWithStats.BytesWritten(),
					time.Since(start),
				)
			}()

			next.ServeHTTP(writerWithStats, request)
		}

		return http.HandlerFunc(handlerFunc)
	}
}
