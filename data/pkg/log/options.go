package log

import (
	"fmt"
	"io"
)

const (
	_secondsFormat = "2006-01-02 15:04:05 "
)

// Option представляет настройки логирования.
type Option func(l *Logger)

// Name устанавливает имя.
func Name(name string) Option {
	return func(l *Logger) {
		l.name = fmt.Sprint(name, " ")
	}
}

// Writer определяет куда писать логи.
func Writer(w io.Writer) Option {
	return func(l *Logger) {
		l.writer = w
	}
}

// TimeWithSeconds устанавливает формат отображения времени с точностью до секунд.
func TimeWithSeconds() Option {
	return func(l *Logger) {
		l.format = _secondsFormat
	}
}
