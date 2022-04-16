package nasdaq

import (
	"context"
	"encoding/json"
	"fmt"
	"golang.org/x/exp/slices"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
)

const (
	_url        = `https://api.nasdaq.com/api/quote/%s/dividends?assetclass=stocks`
	_agentKey   = `User-Agent`
	_agentValue = `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15`

	_noDate         = `N/A`
	_apiDate        = `01/02/2006`
	_currencyPrefix = `$`
)

type nasdaqAPI struct {
	Data struct {
		Dividends struct {
			Rows []struct {
				Date  string `json:"recordDate"`
				Value string `json:"amount"`
			} `json:"rows"`
		} `json:"dividends"`
	} `json:"data"`
}

type gateway struct {
	statusRepo repo.Read[domain.DivStatus]
	client     *http.Client
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.CurrencyDiv]) ([]domain.CurrencyDiv, error) {
	divStatus, err := s.statusRepo.Get(ctx, domain.NewDivStatusID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load dividends status from repo -> %w",
			err,
		)
	}

	statusRows := divStatus.Rows()
	ticker := string(table.Name())

	position := sort.Search(
		len(statusRows),
		func(i int) bool { return statusRows[i].Ticker >= ticker },
	)

	nasdaq := table.Rows()

	for _, row := range statusRows[position:] {
		if row.Ticker != ticker {
			return nil, nil
		}

		n := sort.Search(
			len(nasdaq),
			func(i int) bool { return !nasdaq[i].Date.Before(row.Date) },
		)

		if (n < len(nasdaq)) && row.Date.Equal(nasdaq[n].Date) {
			continue
		}

		rows, err := s.download(ctx, ticker)
		if err != nil {
			return nil, err
		}

		sort.Slice(rows, func(i, j int) bool { return rows[i].Date.Before(rows[j].Date) })

		if slices.Equal(rows, table.Rows()) {
			return nil, nil
		}

		return rows, nil
	}

	return nil, nil
}

func (s gateway) download(ctx context.Context, ticker string) ([]domain.CurrencyDiv, error) {
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		fmt.Sprintf(_url, strings.TrimSuffix(ticker, _foreignSuffix)),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare NASDAQ request for %s -> %w", ticker, err)
	}

	request.Header.Add(_agentKey, _agentValue)

	respond, err := s.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get NASDAQ respond for %s -> %w", ticker, err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get NASDAQ status %s for %s", respond.Status, ticker)
	}

	return parseRequest(respond)
}

func parseRequest(respond *http.Response) ([]domain.CurrencyDiv, error) {
	var nasdaq nasdaqAPI

	decoder := json.NewDecoder(respond.Body)
	if err := decoder.Decode(&nasdaq); err != nil {
		return nil, fmt.Errorf("can't decode NASDAQ json -> %w", err)
	}

	var rows []domain.CurrencyDiv

	for _, row := range nasdaq.Data.Dividends.Rows {
		if row.Date == _noDate {
			continue
		}
		date, err := time.Parse(_apiDate, row.Date)
		if err != nil {
			return nil, fmt.Errorf("can't parse date %s -> %w", row.Date, err)
		}

		if !strings.HasPrefix(row.Value, _currencyPrefix) {
			return nil, fmt.Errorf("wrong currency prefix %s ", row.Value)
		}

		value, err := strconv.ParseFloat(strings.TrimPrefix(row.Value, _currencyPrefix), 64)
		if err != nil {
			return nil, fmt.Errorf("can't parse dividend %s -> %w", row.Value, err)
		}

		rows = append(rows, domain.CurrencyDiv{
			Date:     date,
			Value:    value,
			Currency: domain.USDCurrency,
		})
	}

	return rows, nil
}
