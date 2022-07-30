package mocks

import (
	"context"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/stretchr/testify/mock"
)

type Repo[E domain.Entity] struct {
	mock.Mock
}

func (m *Repo[E]) Get(_ context.Context, qid domain.QID) (domain.Aggregate[E], error) {
	args := m.Called(qid)

	return args.Get(0).(domain.Aggregate[E]), args.Error(1)
}

func (m *Repo[E]) Save(_ context.Context, agg domain.Aggregate[E]) error {
	args := m.Called(agg)

	return args.Error(0)
}
