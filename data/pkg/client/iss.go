package client

import (
	"net/http"

	"github.com/WLM1ke/gomoex"
)

// ISS - создает клиент для ISS с ограничением на количество соединений.
func ISS(maxCons int) *gomoex.ISSClient {
	http := &http.Client{
		Transport: &http.Transport{
			MaxConnsPerHost: maxCons,
		},
	}

	return gomoex.NewISSClient(http)
}
