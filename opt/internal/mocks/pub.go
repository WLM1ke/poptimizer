package mocks

import (
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/stretchr/testify/mock"
)

type Pub struct {
	mock.Mock
}

func (m *Pub) Publish(event domain.Event) {
	m.Called(event)
}
