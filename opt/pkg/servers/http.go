package servers

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
)

// Server представляет обертку над http сервером.
type Server struct {
	srv http.Server
}

// NewHTTPServer - создает http сервер.
func NewHTTPServer(log lgr.Logger, addr string, handler http.Handler, requestTimeouts time.Duration) *Server {
	router := chi.NewRouter()
	router.Use(middleware.Timeout(requestTimeouts))
	router.Use(logging(log))
	router.Use(middleware.RedirectSlashes)
	router.Mount("/", handler)

	return &Server{
		srv: http.Server{
			Addr:              addr,
			Handler:           router,
			ReadTimeout:       requestTimeouts,
			ReadHeaderTimeout: requestTimeouts,
			WriteTimeout:      requestTimeouts,
		},
	}
}

// Run запускает http сервер.
func (s *Server) Run(ctx context.Context) error {
	closed := make(chan error)

	go func() {
		<-ctx.Done()

		if err := s.srv.Shutdown(context.Background()); err != nil {
			closed <- fmt.Errorf("can't close server connections: %w", err)
		}

		close(closed)
	}()

	if err := s.srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("unexpected server shutdown: %w", err)
	}

	return <-closed
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

// WriteJSON посылает DTO в виде JSON и логирует ошибку.
func WriteJSON(logger lgr.Logger, writer http.ResponseWriter, dto any) {
	writer.Header().Set("Content-Type", "application/json; charset=UTF-8")

	if err := json.NewEncoder(writer).Encode(dto); err != nil {
		http.Error(writer, err.Error(), http.StatusInternalServerError)
		logger.Warnf("can't encode dto -> %s", err)

		return
	}
}
