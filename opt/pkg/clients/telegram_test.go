package clients

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"sync"
	"testing"

	"github.com/go-chi/chi"
	"github.com/stretchr/testify/assert"
)

func mockTelegramServer() *httptest.Server {
	router := chi.NewRouter()

	router.Get("/bad-token/getChat", func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"error_code": 400, "description": "Some error"}`, http.StatusBadRequest)
	})
	router.Get("/good-token/getChat", func(writer http.ResponseWriter, request *http.Request) {
		err := request.ParseForm()
		if err != nil {
			http.Error(writer, err.Error(), http.StatusBadRequest)

			return
		}

		if request.Form.Get("chat_id") == "good-id" {
			_, _ = writer.Write([]byte(""))
		}

		http.Error(writer, `{"error_code": 400, "description": "Bad chat_id"}`, http.StatusBadRequest)
	})
	router.Get("/good-token/SendMessage", func(writer http.ResponseWriter, request *http.Request) {
		err := request.ParseForm()
		if err != nil {
			http.Error(writer, err.Error(), http.StatusBadRequest)

			return
		}

		if request.Form.Get("chat_id") != "good-id" {
			http.Error(writer, `{"error_code": 400, "description": "Bad chat_id"}`, http.StatusBadRequest)

			return
		}
		if request.Form.Get("text") != `\!Msg` {
			http.Error(writer, `{"error_code": 400, "description": "Bad message"}`, http.StatusBadRequest)

			return
		}
		if request.Form.Get("disable_web_page_preview") != "true" {
			http.Error(writer, `{"error_code": 400, "description": "Bad preview"}`, http.StatusBadRequest)

			return
		}
		if request.Form.Get("parse_mode") != "MarkdownV2" {
			http.Error(writer, `{"error_code": 400, "description": "Bad format"}`, http.StatusBadRequest)

			return
		}

		_, _ = writer.Write([]byte(""))
	})

	return httptest.NewServer(router)
}

func TestTelegramPingBadToken(t *testing.T) {
	t.Parallel()

	ts := mockTelegramServer()
	defer ts.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: ts.URL + "/%s/%s",
		token:   "bad-token",
		chatID:  "some",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.EqualError(
		t, telegram.ping(ctx),
		"telegram status code 400 -> Some error",
		"Не работает пинг некорректного токена",
	)
}

func TestTelegramPingBadID(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: server.URL + "/%s/%s",
		token:   "good-token",
		chatID:  "bad-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.EqualError(
		t, telegram.ping(ctx),
		"telegram status code 400 -> Bad chat_id",
		"Не работает пинг некорректного чата",
	)
}

func TestTelegramPing(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: server.URL + "/%s/%s",
		token:   "good-token",
		chatID:  "good-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.Nil(t, telegram.ping(ctx), "Не работает пинг корректного токена")
}

func TestTelegramSendError(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: server.URL + "/%s/%s",
		token:   "good-token",
		chatID:  "bad-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.EqualError(
		t, telegram.Send(ctx, "!Msg"),
		"telegram status code 400 -> Bad chat_id",
		"Не работает пинг некорректного чата",
	)
}

func TestTelegramSend(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: server.URL + "/%s/%s",
		token:   "good-token",
		chatID:  "good-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.Nil(t, telegram.Send(ctx, "!Msg"), "Не работает посылка сообщений")
}

func TestCallBadRequest(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: "",
		token:   "good-token",
		chatID:  "good-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.ErrorContains(
		t, telegram.apiCall(ctx, "!Msg"),
		"can't create telegram request",
		"Не работает обработка ошибок в подготовке запроса",
	)
}

func TestCallBadRequestExec(t *testing.T) {
	t.Parallel()

	server := mockTelegramServer()
	defer server.Close()

	telegram := Telegram{
		client:  &http.Client{},
		apiTmpl: "%s%s",
		token:   "good-token",
		chatID:  "good-id",
		lock:    sync.Mutex{},
	}

	ctx := context.Background()

	assert.ErrorContains(
		t, telegram.apiCall(ctx, "!Msg"),
		"can't make telegram request",
		"Не работает обработка ошибок в выполнении запроса",
	)
}

func TestPrepareMsg(t *testing.T) {
	t.Parallel()

	in := `a+!()-_.>{}b`
	out := url.QueryEscape(`a\+\!\(\)\-\_\.\>\{\}b`)

	assert.Equal(t, out, prepareMsg(in), "Неправильная обработка специальных символов в сообщении")
}

func TestParseErrorBadAnswer(t *testing.T) {
	t.Parallel()

	in := bytes.NewReader([]byte(`}`))
	out := "can't parse telegram error body"

	assert.ErrorContains(t, parseError(in), out, "Не обрабатывается ошибка парсинга")
}

func TestParseError(t *testing.T) {
	t.Parallel()

	in := bytes.NewReader([]byte(`{"error_code": 42, "description": "Some error"}`))
	out := "telegram status code 42 -> Some error"

	assert.EqualError(t, parseError(in), out, "Не работает парсинг ошибки")
}
