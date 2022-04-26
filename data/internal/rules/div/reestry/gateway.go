package reestry

import (
	"context"
	"fmt"
	"net/http"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"golang.org/x/exp/slices"
)

const (
	_url             = `https://закрытияреестров.рф/%s/`
	_preferredType   = `2`
	_preferredSuffix = `P`

	_rual  = `_RUAL`
	_rualr = `_RUALR`

	_dateFormat = `_2.01.2006`
)

var (
	_datePattern = regexp.MustCompile(`\d{1,2}\.\d{2}\.\d{4}`)
	_divPattern  = regexp.MustCompile(`(\d+|\d+,\d+).(руб|USD|\$)`)
)

type gateway struct {
	status     repo.Read[domain.DivStatus]
	securities repo.Read[domain.Security]
	client     *http.Client
}

func (s gateway) Get(ctx context.Context, table domain.Table[domain.CurrencyDiv]) ([]domain.CurrencyDiv, error) {
	divStatus, err := s.status.Get(ctx, domain.NewDivStatusID())
	if err != nil {
		return nil, fmt.Errorf(
			"can't load dividends status from repo -> %w",
			err,
		)
	}

	statusRows := divStatus.Rows()
	ticker := string(table.Name())

	tickerPosition := sort.Search(
		len(statusRows),
		func(i int) bool { return statusRows[i].Ticker >= ticker },
	)

	reestry := table.Rows()

	for _, row := range statusRows[tickerPosition:] {
		if row.Ticker != ticker {
			return nil, nil
		}

		datePosition := sort.Search(
			len(reestry),
			func(i int) bool { return !reestry[i].Date.Before(row.Date) },
		)

		if (datePosition < len(reestry)) && row.Date.Equal(reestry[datePosition].Date) {
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
	preferred, err := s.isPreferred(ctx, ticker)
	if err != nil {
		return nil, err
	}

	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		makeURL(ticker, preferred),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare CloseReestry request for %s -> %w", ticker, err)
	}

	respond, err := s.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get CloseReestry respond for %s -> %w", ticker, err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get CloseReestry status %s for %s", respond.Status, ticker)
	}

	return parseRequest(respond, strings.HasSuffix(ticker, _preferredSuffix))
}

func (s gateway) isPreferred(ctx context.Context, ticker string) (bool, error) {
	sec, err := s.securities.Get(ctx, domain.NewSecuritiesID())
	if err != nil {
		return false, fmt.Errorf("can't load securities -> %w", err)
	}

	rows := sec.Rows()

	tickerPosition := sort.Search(
		len(rows),
		func(i int) bool { return rows[i].Ticker >= ticker },
	)

	if tickerPosition < len(rows) && rows[tickerPosition].Ticker == ticker {
		return rows[tickerPosition].Type == _preferredType, nil
	}

	return false, fmt.Errorf("can't find %s in securities", ticker)
}

func makeURL(ticker string, preferred bool) string {
	if preferred {
		ticker = strings.TrimSuffix(ticker, _preferredSuffix)
	}

	if ticker == _rual {
		return fmt.Sprintf(_url, _rualr)
	}

	return fmt.Sprintf(_url, ticker)
}

func parseRequest(respond *http.Response, preferred bool) ([]domain.CurrencyDiv, error) {
	html, err := goquery.NewDocumentFromReader(respond.Body)
	if err != nil {
		return nil, fmt.Errorf("can't parse CloseReestry html -> %w", err)
	}

	table := html.Find("tbody").Find("tr")

	err = validateHeader(table, preferred)
	if err != nil {
		return nil, err
	}

	nodes := table.Slice(1, goquery.ToEnd).Nodes
	rows := make([]domain.CurrencyDiv, 0, len(nodes))

	for _, node := range nodes {
		htmlRow := goquery.NewDocumentFromNode(node)
		if strings.Contains(htmlRow.Text(), "ИТОГО") {
			continue
		}

		if strings.Contains(htmlRow.Text(), "НЕ ВЫПЛАЧИВАТЬ") {
			continue
		}

		row, err := parseRow(htmlRow, preferred)
		if err != nil {
			return nil, err
		}

		rows = append(rows, row)
	}

	return rows, nil
}

func validateHeader(selection *goquery.Selection, preferred bool) error {
	if preferred {
		header := selection.First().Find("td:nth-child(3)").Text()

		if !strings.Contains(header, "привилегированную") {
			return fmt.Errorf("can't find preferred in header - %s", header)
		}
	}

	header := selection.First().Find("td:nth-child(2)").Text()

	if !strings.Contains(header, "обыкновенную") {
		return fmt.Errorf("can't find common in header - %s", header)
	}

	return nil
}

func parseRow(htmlRow *goquery.Document, preferred bool) (row domain.CurrencyDiv, err error) {
	dateStr := htmlRow.Find("td:nth-child(1)").Text()

	row.Date, err = time.Parse(_dateFormat, _datePattern.FindString(dateStr))
	if err != nil {
		return domain.CurrencyDiv{}, fmt.Errorf("can't parse date %s -> %w", dateStr, err)
	}

	valueStr := htmlRow.Find("td:nth-child(2)").Text()
	if preferred {
		valueStr = htmlRow.Find("td:nth-child(3)").Text()
	}

	values := _divPattern.FindStringSubmatch(valueStr)
	if values == nil {
		return domain.CurrencyDiv{}, fmt.Errorf("can't parse value %s -> %w", valueStr, err)
	}

	row.Value, err = strconv.ParseFloat(strings.Replace(values[1], ",", ".", 1), 64)
	if err != nil {
		return domain.CurrencyDiv{}, fmt.Errorf("can't parse dividend %s -> %w", values[1], err)
	}

	switch values[2] {
	case "руб":
		row.Currency = domain.RURCurrency
	case "USD", "$":
		row.Currency = domain.USDCurrency
	default:
		return domain.CurrencyDiv{}, fmt.Errorf("can't parse currency - %s", values[2])
	}

	return row, nil
}
