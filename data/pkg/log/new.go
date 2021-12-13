package log

import (
	"io"
	"os"
)

// WithOptions создает логер в соответствии с настройками.
func WithOptions(options ...Option) *Logger {
	log := Logger{}
	log.pool = newPool()

	for _, opt := range options {
		opt(&log)
	}

	return &log
}

// New - логер с именем, отображением времени до секунд и записью в stderr.
func New(name string) *Logger {
	return WithOptions(Writer(os.Stderr), TimeWithSeconds(), Name(name))
}

// NoOp не пишет логи - предназначен для тестирования.
//
// Логирование на уровне Panicf вызывает панику.
func NoOp() *Logger {
	return WithOptions(Writer(io.Discard), TimeWithSeconds())
}
