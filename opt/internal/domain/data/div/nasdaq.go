package div

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"golang.org/x/exp/slices"
)

const (
	_NASDAQurl        = `https://api.nasdaq.com/api/quote/%s/dividends?assetclass=stocks`
	_NASDAQAgentKey   = `User-Agent`
	_NASDAQAgentValue = `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15` //nolint:lll

	_NASDAQNoDate         = `N/A`
	_NASDAQapiDate        = `01/02/2006`
	_NASDAQCurrencyPrefix = `$`
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

// CheckNASDAQHandler обработчик событий, отвечающий за проверку дивидендов на NASDAQ.
type CheckNASDAQHandler struct {
	pub    domain.Publisher
	repo   domain.ReadWriteRepo[RawTable]
	client *http.Client
}

// NewCheckNASDAQHandler новый обработчик событий, отвечающий за проверку дивидендов на NASDAQ.
func NewCheckNASDAQHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[RawTable],
	client *http.Client,
) *CheckNASDAQHandler {
	return &CheckNASDAQHandler{
		repo:   repo,
		pub:    pub,
		client: client,
	}
}

// Match выбирает события изменения статуса дивидендов по иностранным тикерам.
func (h CheckNASDAQHandler) Match(event domain.Event) bool {
	status, ok := event.Data.(Status)

	return ok && status.Foreign && event.QualifiedID == StatusID(event.ID)
}

func (h CheckNASDAQHandler) String() string {
	return "dividend status foreign -> check NASDAQ"
}

// Handle реагирует на событие об обновлении статуса дивидендов и обновляет дивиденды с NASDAQ.
func (h CheckNASDAQHandler) Handle(ctx context.Context, event domain.Event) {
	status, ok := event.Data.(Status)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := NASDAQid(event.ID)

	event.QualifiedID = qid

	agg, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if agg.Entity.Exists(status.Date) {
		return
	}

	table, err := h.download(ctx, status)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	sort.Slice(table, func(i, j int) bool { return table[i].Date.Before(table[j].Date) })

	if slices.Equal(table, agg.Entity) {
		return
	}

	agg.Timestamp = event.Timestamp
	agg.Entity = table

	if err := h.repo.Save(ctx, agg); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}
}

func (h CheckNASDAQHandler) download(ctx context.Context, status Status) (RawTable, error) {
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		fmt.Sprintf(_NASDAQurl, status.BaseTicker),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare NASDAQ request for %s -> %w", status.Ticker, err)
	}

	request.Header.Add(_NASDAQAgentKey, _NASDAQAgentValue)

	respond, err := h.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get NASDAQ respond for %s -> %w", status.Ticker, err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get NASDAQ status %s for %s", respond.Status, status.Ticker)
	}

	return parseNASDAQRequest(respond)
}

func parseNASDAQRequest(respond *http.Response) (RawTable, error) {
	var nasdaq nasdaqAPI

	decoder := json.NewDecoder(respond.Body)
	if err := decoder.Decode(&nasdaq); err != nil {
		return nil, fmt.Errorf("can't decode NASDAQ json -> %w", err)
	}

	rows := make(RawTable, 0, len(nasdaq.Data.Dividends.Rows))

	for _, row := range nasdaq.Data.Dividends.Rows {
		if row.Date == _NASDAQNoDate {
			continue
		}

		date, err := time.Parse(_NASDAQapiDate, row.Date)
		if err != nil {
			return nil, fmt.Errorf("can't parse date %s -> %w", row.Date, err)
		}

		if !strings.HasPrefix(row.Value, _NASDAQCurrencyPrefix) {
			return nil, fmt.Errorf("wrong currency prefix %s ", row.Value)
		}

		value, err := strconv.ParseFloat(strings.TrimPrefix(row.Value, _NASDAQCurrencyPrefix), 64)
		if err != nil {
			return nil, fmt.Errorf("can't parse dividend %s -> %w", row.Value, err)
		}

		rows = append(rows, Raw{
			Date:     date,
			Value:    value,
			Currency: USDCurrency,
		})
	}

	return rows, nil
}
