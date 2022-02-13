package status

import (
	"context"
	"encoding/csv"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"golang.org/x/text/encoding/charmap"
	"io"
	"net/http"
	"regexp"
	"sort"
	"time"
)

const (
	_url        = `https://www.moex.com/ru/listing/listing-register-closing-csv.aspx`
	_dateFormat = `02.01.2006 15:04:05`
	_pastDays   = 0
)

var reTicker = regexp.MustCompile(`, ([A-Z]+-[A-Z]+|[A-Z]+) \[`)

type gateway struct {
	client *http.Client
}

func (g gateway) Get(
	ctx context.Context,
	_ domain.Table[DivStatus],
	date time.Time,
) ([]DivStatus, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _url, http.NoBody)
	if err != nil {
		return nil, fmt.Errorf(
			"%w: can't create request -> %s",
			template.ErrRuleGateway,
			err,
		)
	}

	resp, err := g.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf(
			"%w: can't make request -> %s",
			template.ErrRuleGateway,
			err,
		)
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf(
			"%w: bad respond status %s",
			template.ErrRuleGateway,
			resp.Status,
		)
	}

	decoder := charmap.Windows1251.NewDecoder()
	reader := csv.NewReader(decoder.Reader(resp.Body))

	return parceCSV(reader, date)
}

func parceCSV(reader *csv.Reader, date time.Time) (rows []DivStatus, err error) {
	header := true

	for record, err := reader.Read(); err != io.EOF; record, err = reader.Read() {
		switch {
		case err != nil:
			return nil, fmt.Errorf(
				"%w: can't parse row %s -> %s",
				template.ErrRuleGateway,
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
				"%w: can't parse date %s ->  %s",
				template.ErrRuleGateway,
				record[1],
				err,
			)
		}

		if divDate.Before(date.AddDate(0, 0, -_pastDays)) {
			continue
		}

		ticker := reTicker.FindStringSubmatch(record[0])
		if ticker == nil {
			return nil, fmt.Errorf(
				"%w: can't parse ticker %s ->  %s",
				template.ErrRuleGateway,
				record[0],
				err,
			)
		}

		rows = append(rows, DivStatus{
			Ticker: ticker[1],
			Date:   divDate,
		})
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
