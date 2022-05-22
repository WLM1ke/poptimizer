package lgr

import (
	"io"
)

const (
	_timeWithSecondsFormat = "2006-01-02 15:04:05 "
)

// Option представляет настройки логирования.
type Option func(l *Logger)

// Prefix устанавливает префикс.
func Prefix(prefix string) Option {
	return func(l *Logger) {
		l.prefix = prefix + ": "
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
		l.timeFormat = _timeWithSecondsFormat
	}
}
