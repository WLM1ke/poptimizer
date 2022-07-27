package servers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
)

// Server представляет обертку над http сервером.
type Server struct {
	logger lgr.Logger
	srv    http.Server
}

// NewHTTPServer - создает http сервер.
func NewHTTPServer(logger lgr.Logger, addr string, handler http.Handler, respondTimeouts time.Duration) *Server {
	router := chi.NewRouter()
	router.Use(middleware.Timeout(respondTimeouts))
	router.Use(logging(logger))
	router.Use(middleware.RedirectSlashes)
	router.Mount("/", handler)

	return &Server{
		logger: logger,
		srv: http.Server{
			Addr:              addr,
			Handler:           router,
			ReadTimeout:       respondTimeouts,
			ReadHeaderTimeout: respondTimeouts,
			WriteTimeout:      respondTimeouts,
		},
	}
}

// Run запускает http сервер.
func (s *Server) Run(ctx context.Context) {
	go func() {
		<-ctx.Done()

		if err := s.srv.Shutdown(context.Background()); err != nil {
			s.logger.Warnf("can't close server connections: %s", err)
		}
	}()

	if err := s.srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		s.logger.Warnf("unexpected server shutdown: %s", err)
	}
}

func logging(logger lgr.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		handlerFunc := func(writer http.ResponseWriter, request *http.Request) {
			writerWithStats := middleware.NewWrapResponseWriter(writer, request.ProtoMajor)
			start := time.Now()

			defer func() {
				status := writerWithStats.Status()

				logFunc := logger.Infof

				if status >= http.StatusBadRequest {
					logFunc = logger.Warnf
				}

				logFunc(
					"%s %s %d %db %s",
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

// WriteJSON посылает DTO в виде JSON.
func WriteJSON(writer http.ResponseWriter, dto any) {
	writer.Header().Set("Content-Type", "application/json; charset=UTF-8")

	if err := json.NewEncoder(writer).Encode(dto); err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)

		return
	}
}
