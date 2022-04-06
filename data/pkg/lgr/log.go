package lgr

import (
	"fmt"
	"io"
	"sync"
)

const (
	_infoColored  = "\033[34mINFO \033[0m"
	_warnColored  = "\033[33mWARN \033[0m"
	_panicColored = "\033[31mPANIC \033[0m"

	end = "\n"
)

// Logger простой логер.
type Logger struct {
	name   string
	writer io.Writer
	format string

	lock sync.Mutex
	pool pool
}

func (l *Logger) logf(level, format string, args ...interface{}) {
	buf := l.pool.get()
	defer func() {
		l.pool.put(buf)
	}()

	buf.appendNow(l.format)
	buf.appendString(level)
	buf.appendString(l.name)
	buf.appendStringf(format, args...)
	buf.appendString(end)

	l.lock.Lock()
	defer l.lock.Unlock()

	l.writer.Write(buf.bs) //nolint:errcheck
}

// Infof записывает в лог сообщение, не требующее реакции разработчика.
func (l *Logger) Infof(format string, args ...interface{}) {
	l.logf(_infoColored, format, args...)
}

// Warnf записывает в лог сообщение, требующее реакции разработчика.
func (l *Logger) Warnf(format string, args ...interface{}) {
	l.logf(_warnColored, format, args...)
}

// Panicf записывает в лог сообщение и паникует.
func (l *Logger) Panicf(format string, args ...interface{}) {
	defer func() {
		panic(fmt.Sprintf(format, args...))
	}()

	l.logf(_panicColored, format, args...)
}
