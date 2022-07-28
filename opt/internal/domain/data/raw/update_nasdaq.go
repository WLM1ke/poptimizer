package raw

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
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

// NASDAQService обновляет данные с NASDAQ.
type NASDAQService struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	client *http.Client
}

// NewNASDAQService создает службу обновления данных с NASDAQ.
func NewNASDAQService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	client *http.Client,
) *NASDAQService {
	return &NASDAQService{
		logger: logger,
		repo:   repo,
		client: client,
	}
}

// Update данные с NASDAQ, если локальная версия не содержит ожидаемых дивидендов и не обновлялась сегодня.
func (s NASDAQService) Update(ctx context.Context, date time.Time, table StatusTable) {
	defer s.logger.Infof("update is finished")

	for _, status := range table {
		if !status.Foreign {
			continue
		}

		if err := s.updateOne(ctx, date, status); err != nil {
			s.logger.Warnf("%s", err)
		}
	}
}

func (s NASDAQService) updateOne(ctx context.Context, date time.Time, status Status) error {
	agg, err := s.repo.Get(ctx, NasdaqID(status.Ticker))
	if err != nil {
		return err
	}

	rowsOld := agg.Entity()

	if rowsOld.ExistsDate(status.Date) || agg.Timestamp().Equal(date) {
		return nil
	}

	rowsNew, err := s.download(ctx, status)
	if err != nil {
		return fmt.Errorf("%s for %w", status.Ticker, err)
	}

	rowsNew.Sort()

	if slices.Equal(rowsNew, rowsOld) {
		return nil
	}

	agg.Update(rowsNew, date)

	if err := s.repo.Save(ctx, agg); err != nil {
		return err
	}

	return nil
}

func (s NASDAQService) download(ctx context.Context, status Status) (Table, error) {
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		fmt.Sprintf(_NASDAQurl, status.BaseTicker),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare request -> %w", err)
	}

	request.Header.Add(_NASDAQAgentKey, _NASDAQAgentValue)

	respond, err := s.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get respond for %s -> %w", status.Ticker, err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("bad respond code %s", respond.Status)
	}

	return parseNASDAQRequest(respond)
}

func parseNASDAQRequest(respond *http.Response) (Table, error) {
	var nasdaq nasdaqAPI

	decoder := json.NewDecoder(respond.Body)
	if err := decoder.Decode(&nasdaq); err != nil {
		return nil, fmt.Errorf("can't decode json -> %w", err)
	}

	rows := make(Table, 0, len(nasdaq.Data.Dividends.Rows))

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
