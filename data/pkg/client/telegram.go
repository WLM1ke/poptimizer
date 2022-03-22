package client

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sync"
	"time"

	"github.com/pkg/errors"
)

const (
	_apiTemplate = `https://api.telegram.org/bot%s/%s`

	_pingCmd = `getChat?chat_id=%s`
	_sendCmd = `SendMessage?chat_id=%s&text=%s&disable_web_page_preview=true&parse_mode=MarkdownV2`

	_pingTimeout = time.Second * 5
)

var (
	errTelegramAPI = errors.New(`telegram api error`)
	escapeRe       = regexp.MustCompile(`[()-_.>{}]`)
)

// Telegram - клиент для рассылки с помощью бота сообщения в определенный чат.
//
// Может использоваться из нескольких горутин.
type Telegram struct {
	client *http.Client

	token  string
	chatID string

	sync.Mutex
}

// NewTelegram создает новый клиент для Telegram.
//
// При создании проверяет корректность введенного токена и id.
func NewTelegram(client *http.Client, token, chatID string) (*Telegram, error) {
	telegram := Telegram{
		client: client,
		token:  token,
		chatID: chatID,
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
	t.Mutex.Lock()
	defer t.Mutex.Unlock()

	for _, msg := range markdowns {
		msg = escapeRe.ReplaceAllStringFunc(msg, func(ex string) string { return `\` + ex })
		cmd := fmt.Sprintf(_sendCmd, t.chatID, msg)

		err := t.apiCall(ctx, cmd)
		if err != nil {
			return err
		}
	}

	return nil
}

func (t *Telegram) apiCall(ctx context.Context, cmd string) error {
	url := fmt.Sprintf(_apiTemplate, t.token, cmd)

	req, err := http.NewRequestWithContext(ctx, "GET", url, http.NoBody)
	if err != nil {
		return fmt.Errorf("%w: can't create request -> %s", errTelegramAPI, err)
	}

	resp, err := t.client.Do(req)
	if err != nil {
		return fmt.Errorf("%w: can't make request -> %s", errTelegramAPI, err)
	}
	defer resp.Body.Close() //nolint:errcheck

	if resp.StatusCode != http.StatusOK {
		return t.parseError(resp.Body)
	}

	return nil
}

func (t *Telegram) parseError(reader io.Reader) error {
	var tgErr struct {
		ErrorCode   int    `json:"error_code"`
		Description string `json:"description"`
	}

	if err := json.NewDecoder(reader).Decode(&tgErr); err != nil {
		return fmt.Errorf("%w: can't parse error body -> %s", errTelegramAPI, err)
	}

	return fmt.Errorf("%w: status code %d -> %s", errTelegramAPI, tgErr.ErrorCode, tgErr.Description)
}
