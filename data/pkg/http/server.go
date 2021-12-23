package http

import (
	"context"
	"errors"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/pkg/log"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
	"net/http"
	"time"
)

// Server представляет http сервер.
type Server struct {
	log             *log.Logger
	addr            string
	requestTimeouts time.Duration
	handler         http.Handler
}

// NewServer - создает http сервер.
func NewServer(log *log.Logger, addr string, requestTimeouts time.Duration, handler http.Handler) *Server {
	return &Server{log: log, addr: addr, requestTimeouts: requestTimeouts, handler: handler}
}

// Run запускает http сервер.
func (s *Server) Run(ctx context.Context) error {
	router := chi.NewRouter()
	router.Use(middleware.Timeout(s.requestTimeouts))
	router.Use(Middleware(s.log))
	router.Use(middleware.RedirectSlashes)
	router.Mount("/", s.handler)

	srv := http.Server{
		Addr:         s.addr,
		Handler:      router,
		ReadTimeout:  s.requestTimeouts,
		WriteTimeout: s.requestTimeouts,
	}

	closed := make(chan error)

	go func() {
		<-ctx.Done()

		if err := srv.Shutdown(context.Background()); err != nil {
			closed <- fmt.Errorf("не удалось закрыть соединения сервера: %w", err)
		}

		close(closed)
	}()

	if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("внезапное завершение работы сервера: %w", err)
	}

	return <-closed
}
