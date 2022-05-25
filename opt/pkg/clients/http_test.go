package clients

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestLogger(t *testing.T) {
	t.Parallel()

	transport, ok := NewHTTPClient(42).Transport.(*http.Transport)
	assert.True(t, ok, "Ошибка в приведении типа транспорта")

	assert.Equal(t, 42, transport.MaxConnsPerHost, "Не верное количество соединений на хост")
}
