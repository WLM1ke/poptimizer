package domain

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"sync"
)

// Session позволяет длительно взаимодействовать одним доменным объектом.
//
// Реализована поддержка для одной одновременной сессии, так как нет необходимости в поддержки нескольких одновременных
// сессий.
type Session[T any] struct {
	logger *lgr.Logger
	repo   ReadWriteRepo[T]

	lock sync.Mutex

	session string
	agg     Aggregate[T]
}

// NewSession создает новую сессию.
func NewSession[T any](logger *lgr.Logger, repo ReadWriteRepo[T]) *Session[T] {
	return &Session[T]{logger: logger, repo: repo}
}

// Init создает новую сессию для заданного агрегата. Повторное создание аннулирует предыдущую.
func (s *Session[T]) Init(ctx context.Context, session string, id QualifiedID) error {
	agg, err := s.repo.Get(ctx, id)
	if err != nil {
		return fmt.Errorf("can't load aggregate -> %w", err)
	}

	s.lock.Lock()
	defer s.lock.Unlock()

	s.session = session
	s.agg = agg

	return nil
}

// Acquire берет контроль над доменным объектом для взаимодействия с ним.
func (s *Session[T]) Acquire(session string) (*T, error) {
	s.lock.Lock()

	if s.session != session {
		return nil, fmt.Errorf("wrong session - %s", session)
	}

	return &s.agg.Entity, nil
}

// Release высвобождает ранее захваченный объект.
func (s *Session[T]) Release() {
	s.lock.Unlock()
}

// Save сохраняет агрегат без прекращения сессии взаимодействия с ним.
func (s *Session[T]) Save(ctx context.Context, session string) error {
	s.lock.Lock()
	defer s.lock.Unlock()

	if s.session != session {
		return fmt.Errorf("wrong session - %s", session)
	}

	err := s.repo.Save(ctx, s.agg)
	if err != nil {
		return err
	}

	s.agg, err = s.repo.Get(ctx, s.agg.id)
	if err != nil {
		return fmt.Errorf("can't load new vertion of agg -> %w", err)
	}

	return nil
}
