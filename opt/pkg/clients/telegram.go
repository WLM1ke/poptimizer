package clients

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"sync"
	"time"
)

const (
	_apiTemplate = `https://api.telegram.org/bot%s/%s`

	_pingCmd = `getChat?chat_id=%s`
	_sendCmd = `SendMessage?chat_id=%s&text=%s&disable_web_page_preview=true&parse_mode=MarkdownV2`

	_pingTimeout = time.Second * 5
)

var escapeRe = regexp.MustCompile(`[!()\-_.>{}=+]`)

// Telegram - клиент для конкурентной рассылки сообщений в определенный чат.
type Telegram struct {
	client  *http.Client
	apiTmpl string // Используется для тестирования

	token  string
	chatID string

	lock sync.Mutex
}

// NewTelegram создает новый клиент для Telegram.
//
// При создании проверяет корректность введенного токена и id.
func NewTelegram(client *http.Client, token, chatID string) (*Telegram, error) {
	telegram := Telegram{
		client:  client,
		apiTmpl: _apiTemplate,
		token:   token,
		chatID:  chatID,
	}

	ctx, cancel := context.WithTimeout(context.Background(), _pingTimeout)
	defer cancel()

	if err := telegram.ping(ctx); err != nil {
		return nil, err
	}

	return &telegram, nil
}

func (t *Telegram) ping(ctx context.Context) error {
	cmd := fmt.Sprintf(_pingCmd, t.chatID)

	return t.apiCall(ctx, cmd)
}

// Send посылает сообщение в формате MarkdownV2.
func (t *Telegram) Send(ctx context.Context, markdowns ...string) error {
	t.lock.Lock()
	defer t.lock.Unlock()

	for _, msg := range markdowns {
		cmd := fmt.Sprintf(_sendCmd, t.chatID, prepareMsg(msg))

		err := t.apiCall(ctx, cmd)
		if err != nil {
			return err
		}
	}

	return nil
}

func prepareMsg(msg string) string {
	return url.QueryEscape(escapeRe.ReplaceAllStringFunc(msg, func(ex string) string { return `\` + ex }))
}

func (t *Telegram) apiCall(ctx context.Context, cmd string) error {
	apiURL := fmt.Sprintf(t.apiTmpl, t.token, cmd)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL, http.NoBody)
	if err != nil {
		return fmt.Errorf("can't create telegram request -> %w", err)
	}

	resp, err := t.client.Do(req)
	if err != nil {
		return fmt.Errorf("can't make telegram request -> %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return parseError(resp.Body)
	}

	return nil
}

func parseError(reader io.Reader) error {
	var tgErr struct {
		ErrorCode   int    `json:"error_code"`
		Description string `json:"description"`
	}

	if err := json.NewDecoder(reader).Decode(&tgErr); err != nil {
		return fmt.Errorf("can't parse telegram error body -> %w", err)
	}

	return fmt.Errorf("telegram status code %d -> %s", tgErr.ErrorCode, tgErr.Description)
}
