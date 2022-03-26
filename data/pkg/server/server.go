package server

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
)

// Server представляет http сервер.
type Server struct {
	srv http.Server
}

// NewServer - создает http сервер.
func NewServer(log *lgr.Logger, addr string, handler http.Handler, requestTimeouts time.Duration) *Server {
	router := chi.NewRouter()
	router.Use(middleware.Timeout(requestTimeouts))
	router.Use(Middleware(log))
	router.Use(middleware.RequestID)
	router.Use(middleware.RedirectSlashes)
	router.Mount("/", handler)

	return &Server{
		srv: http.Server{
			Addr:         addr,
			Handler:      router,
			ReadTimeout:  requestTimeouts,
			WriteTimeout: requestTimeouts,
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
