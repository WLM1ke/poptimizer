package lgr

import (
	"fmt"
	"io"
	"sync"
	"time"
)

const (
	_bufferSize = 128

	_infoColored = "\033[34mINFO \033[0m"
	_warnColored = "\033[31mWARN \033[0m"

	_end = "\n"
)

type buffer struct {
	bs []byte
}

func (b *buffer) Write(bs []byte) (int, error) {
	b.bs = append(b.bs, bs...)

	return len(bs), nil
}

func (b *buffer) WriteStringf(format string, args ...any) {
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

// Logger простой логер.
type logger struct {
	prefix     string
	timeFormat string

	pool *bufferPool

	lock   *sync.Mutex
	writer io.Writer
}

// WithPrefix - создает логер с новым префиксом.
func (l *logger) WithPrefix(prefix string) Logger {
	withPrefix := *l
	Prefix(prefix)(&withPrefix)

	return &withPrefix
}

func (l *logger) logf(level, format string, args ...any) {
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
func (l *logger) Infof(format string, args ...any) {
	l.logf(_infoColored, format, args...)
}

// Warnf записывает в лог сообщение, требующее реакции разработчика.
func (l *logger) Warnf(format string, args ...any) {
	l.logf(_warnColored, format, args...)
}
