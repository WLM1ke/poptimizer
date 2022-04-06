package lgr

import (
	"fmt"
	"sync"
	"time"
)

const _size = 128

type pool struct {
	pool *sync.Pool
}

func newPool() pool {
	return pool{
		pool: &sync.Pool{
			New: func() interface{} {
				return &buffer{bs: make([]byte, 0, _size)}
			},
		},
	}
}

func (p *pool) get() *buffer {
	return p.pool.Get().(*buffer) //nolint:forcetypeassert
}

func (p *pool) put(b *buffer) {
	b.reset()
	p.pool.Put(b)
}

// buffer для предварительного формирования записи.
type buffer struct {
	bs []byte
}

func (b *buffer) Write(bs []byte) (n int, err error) {
	b.bs = append(b.bs, bs...)

	return len(bs), nil
}

func (b *buffer) appendString(bs string) {
	b.bs = append(b.bs, bs...)
}

func (b *buffer) appendStringf(format string, args ...interface{}) {
	fmt.Fprintf(b, format, args...)
}

func (b *buffer) appendNow(format string) {
	b.bs = time.Now().AppendFormat(b.bs, format)
}

func (b *buffer) reset() {
	b.bs = b.bs[:0]
}
