package status

import (
	"context"
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"golang.org/x/text/encoding/charmap"
)

const (
	_url        = `https://www.moex.com/ru/listing/listing-register-closing-csv.aspx`
	_dateFormat = `02.01.2006 15:04:05`
	_pastDays   = 0
)

// Акция со странным тикером nompp не торгуется, но попадает в отчеты.
var reTicker = regexp.MustCompile(`, ([A-Z]+-[A-Z]+|[A-Z]+|nompp) \[`)

type gateway struct {
	client *http.Client
	repo   repo.Read[domain.Position]
}

func (g gateway) Get(
	ctx context.Context,
	_ domain.Table[domain.DivStatus],
) ([]domain.DivStatus, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _url, http.NoBody)
	if err != nil {
		return nil, fmt.Errorf(
			"can't create request -> %w",
			err,
		)
	}

	resp, err := g.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf(
			"can't make request -> %w",
			err,
		)
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf(
			"bad respond status %s",
			resp.Status,
		)
	}

	decoder := charmap.Windows1251.NewDecoder()
	reader := csv.NewReader(decoder.Reader(resp.Body))

	rows, err := g.parceCSV(ctx, reader)
	if err != nil {
		return nil, err
	}

	sort.Slice(
		rows,
		func(i, j int) bool {
			if rows[i].Ticker < rows[j].Ticker {
				return true
			}

			if (rows[i].Ticker == rows[j].Ticker) && rows[i].Date.Before(rows[j].Date) {
				return true
			}

			return false
		},
	)

	return rows, nil
}

func (g gateway) parceCSV(ctx context.Context, reader *csv.Reader) (rows []domain.DivStatus, err error) {
	header := true

	positions, err := g.getPositions(ctx)
	if err != nil {
		return nil, err
	}

	for record, err := reader.Read(); !errors.Is(err, io.EOF); record, err = reader.Read() {
		switch {
		case err != nil:
			return nil, fmt.Errorf(
				"can't parse row %s -> %w",
				record,
				err,
			)
		case header:
			header = false

			continue
		}

		divDate, err := time.Parse(_dateFormat, record[1])
		if err != nil {
			return nil, fmt.Errorf(
				"can't parse date %s ->  %w",
				record[1],
				err,
			)
		}

		if divDate.Before(domain.LastTradingDate().AddDate(0, 0, -_pastDays)) {
			continue
		}

		ticker := reTicker.FindStringSubmatch(record[0])
		if ticker == nil {
			return nil, fmt.Errorf(
				"can't parse ticker %s",
				record[0],
			)
		}

		if positions[ticker[1]] {
			rows = append(rows, domain.DivStatus{
				Ticker: ticker[1],
				Date:   divDate,
			})
		}
	}

	return rows, nil
}

func (g gateway) getPositions(ctx context.Context) (map[string]bool, error) {
	positions, err := g.repo.Get(ctx, domain.NewPositionsID())
	if err != nil {
		return nil, fmt.Errorf("can't load positions -> %w", err)
	}

	rez := make(map[string]bool, len(positions.Rows()))

	for _, ticker := range positions.Rows() {
		rez[string(ticker)] = true
	}

	return rez, nil
}
