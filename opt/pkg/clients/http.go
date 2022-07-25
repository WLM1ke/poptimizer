package clients

import "net/http"

// NewHTTPClient создает клиент с заданным количеством соединений к одному хосту.
func NewHTTPClient(maxConnsPerHost int) *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			MaxConnsPerHost: maxConnsPerHost,
		},
	}
}
