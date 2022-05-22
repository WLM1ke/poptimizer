package lgr

import (
	"fmt"
	"io"
	"sync"
	"time"
)

const (
	_bufferSize = 128

	_infoColored  = "\033[34mINFO \033[0m"
	_warnColored  = "\033[33mWARN \033[0m"
	_panicColored = "\033[31mPANIC \033[0m"

	_end = "\n"
)

type buffer struct {
	bs []byte
}

func (b *buffer) Write(bs []byte) (int, error) {
	b.bs = append(b.bs, bs...)

	return len(bs), nil
}

func (b *buffer) WriteStringf(format string, args ...interface{}) {
	fmt.Fprintf(b, format, args...)
}

func (b *buffer) WriteNow(format string) {
	b.bs = time.Now().AppendFormat(b.bs, format)
}

func (b *buffer) Reset() {
	b.bs = b.bs[:0]
}

type bufferPool struct {
	pool sync.Pool
}

func newBufferPool() *bufferPool {
	return &bufferPool{
		pool: sync.Pool{
			New: func() interface{} {
				return &buffer{bs: make([]byte, 0, _bufferSize)}
			},
		},
	}
}

func (p *bufferPool) Get() *buffer {
	return p.pool.Get().(*buffer) //nolint:forcetypeassert // есть гарантия, что тип будет корректным
}

func (p *bufferPool) Put(b *buffer) {
	b.Reset()
	p.pool.Put(b)
}

// Logger простой логгер.
type Logger struct {
	prefix     string
	timeFormat string

	pool *bufferPool

	lock   *sync.Mutex
	writer io.Writer
}

// WithPrefix - создает логгер с новым префиксом.
func (l *Logger) WithPrefix(prefix string) *Logger {
	withPrefix := *l
	Prefix(prefix)(&withPrefix)

	return &withPrefix
}

func (l *Logger) logf(level, format string, args ...interface{}) {
	buf := l.pool.Get()
	defer l.pool.Put(buf)

	buf.WriteNow(l.timeFormat)
	buf.WriteStringf(level)
	buf.WriteStringf(l.prefix)
	buf.WriteStringf(format, args...)
	buf.WriteStringf(_end)

	l.lock.Lock()
	defer l.lock.Unlock()

	l.writer.Write(buf.bs) //nolint:gosec,errcheck // если логирование не работает, не понятно куда писать ошибки
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
	l.logf(_panicColored, format, args...)
	panic(fmt.Sprintf(format, args...))
}
