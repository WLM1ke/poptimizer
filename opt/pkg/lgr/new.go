package lgr

import (
	"io"
	"os"
	"sync"
)

// Logger интерфейс для логирования.
//
// Логер может создавать логер с новым префиксом и записывать сообщения трех уровней.
type Logger interface {
	WithPrefix(prefix string) Logger
	Infof(format string, args ...any)
	Warnf(format string, args ...any)
}

// WithOptions создает логер в соответствии с настройками.
func WithOptions(options ...Option) Logger {
	log := logger{
		pool: newBufferPool(),
		lock: &sync.Mutex{},
	}

	for _, opt := range options {
		opt(&log)
	}

	return &log
}

// New логер с отображением времени до секунд и записью в stdout.
func New(prefix string) Logger {
	return WithOptions(Writer(os.Stdout), TimeWithSeconds(), Prefix(prefix))
}

// Discard не пишет логи - предназначен для тестирования.
func Discard() Logger {
	return WithOptions(Writer(io.Discard), TimeWithSeconds())
}
