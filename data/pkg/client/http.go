package client

import "net/http"

func NewHTTPClient(maxConnsPerHost int) *http.Client {
	return &http.Client{
		Transport: &http.Transport{
			MaxConnsPerHost: maxConnsPerHost,
		},
	}
}
