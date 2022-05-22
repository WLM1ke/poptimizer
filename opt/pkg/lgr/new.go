package lgr

import (
	"io"
	"os"
	"sync"
)

// WithOptions создает логгер в соответствии с настройками.
func WithOptions(options ...Option) *Logger {
	log := Logger{
		pool: newBufferPool(),
		lock: &sync.Mutex{},
	}

	for _, opt := range options {
		opt(&log)
	}

	return &log
}

// New - логгер с отображением времени до секунд и записью в stdout.
func New(prefix string) *Logger {
	return WithOptions(Writer(os.Stdout), TimeWithSeconds(), Prefix(prefix))
}

// Discard не пишет логи, но вызывает панику на уровне Panicf - предназначен для тестирования.
func Discard() *Logger {
	return WithOptions(Writer(io.Discard), TimeWithSeconds())
}
