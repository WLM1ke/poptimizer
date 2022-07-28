package raw

import (
	"context"
	"fmt"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"golang.org/x/exp/slices"
)

const (
	_reestryURL = `https://закрытияреестров.рф/%s/`

	_reestryRual  = `RUAL`
	_reestryRualr = `RUALR`

	_reestryDateFormat = `_2.01.2006`
)

var (
	_reestryDatePattern = regexp.MustCompile(`\d{1,2}\.\d{2}\.\d{4}`)
	_reestryDivPattern  = regexp.MustCompile(`(\d.*)[\x{00A0}\s](руб|USD|\$)`)
)

// ReestryService обновляет данные с закрытияреестров.рф.
type ReestryService struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	client *http.Client
}

// NewReestryService создает службу обновления данных с закрытияреестров.рф.
func NewReestryService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	client *http.Client,
) *ReestryService {
	return &ReestryService{
		logger: logger,
		repo:   repo,
		client: client,
	}
}

// Update данные с закрытияреестров.рф, если локальная версия не содержит ожидаемых дивидендов и не обновлялась сегодня.
func (s ReestryService) Update(ctx context.Context, date time.Time, table StatusTable) {
	defer s.logger.Infof("update is finished")

	for _, status := range table {
		if status.Foreign {
			continue
		}

		if err := s.updateOne(ctx, date, status); err != nil {
			s.logger.Warnf("%s", err)
		}
	}
}

func (s ReestryService) updateOne(ctx context.Context, date time.Time, status Status) error {
	agg, err := s.repo.Get(ctx, ReestryID(status.Ticker))
	if err != nil {
		return err
	}

	rowsOld := agg.Entity()

	if rowsOld.ExistsDate(status.Date) || agg.Timestamp().Equal(date) {
		return nil
	}

	rowsNew, err := s.download(ctx, status)
	if err != nil {
		return fmt.Errorf("%s %w", status.Ticker, err)
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

func (s ReestryService) download(ctx context.Context, status Status) (Table, error) {
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		makeURL(status),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare request -> %w", err)
	}

	respond, err := s.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get respond -> %w", err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("bad respond code %s", respond.Status)
	}

	return parseRequest(respond, status.Preferred)
}

func makeURL(status Status) string {
	ticker := status.BaseTicker

	if ticker == _reestryRual {
		ticker = _reestryRualr
	}

	return fmt.Sprintf(_reestryURL, ticker)
}

func parseRequest(respond *http.Response, preferred bool) (Table, error) {
	html, err := goquery.NewDocumentFromReader(respond.Body)
	if err != nil {
		return nil, fmt.Errorf("can't parse html -> %w", err)
	}

	table := html.Find("tbody").Find("tr")

	if err := validateHeader(table, preferred); err != nil {
		return nil, err
	}

	nodes := table.Slice(1, goquery.ToEnd).Nodes
	rows := make(Table, 0, len(nodes))

	for _, node := range nodes {
		htmlRow := goquery.NewDocumentFromNode(node)
		if strings.Contains(htmlRow.Text(), "ИТОГО") {
			continue
		}

		row, err := parseRow(htmlRow, preferred)
		if err != nil {
			return nil, err
		}

		if row.Date.IsZero() {
			continue
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

// Важно парсить сначала значение, так как это позволяет проверить, что дивиденды действительно выплачены.
func parseRow(htmlRow *goquery.Document, preferred bool) (row Raw, err error) {
	valueStr := htmlRow.Find("td:nth-child(2)").Text()
	if preferred {
		valueStr = htmlRow.Find("td:nth-child(3)").Text()
	}

	if strings.Contains(valueStr, "НЕ ВЫПЛАЧИВАТЬ") {
		return Raw{}, nil
	}

	values := _reestryDivPattern.FindStringSubmatch(valueStr)
	if values == nil {
		return Raw{}, fmt.Errorf("can't parse value %s -> %w", valueStr, err)
	}

	values[1] = strings.Replace(values[1], ",", ".", 1)
	values[1] = strings.Replace(values[1], " ", "", 1)

	row.Value, err = strconv.ParseFloat(values[1], 64)
	if err != nil {
		return Raw{}, fmt.Errorf("can't parse dividend %s -> %w", values[1], err)
	}

	switch values[2] {
	case "руб":
		row.Currency = RURCurrency
	case "USD", "$":
		row.Currency = USDCurrency
	default:
		return Raw{}, fmt.Errorf("can't parse currency - %s", values[2])
	}

	date := htmlRow.Find("td:nth-child(1)").Text()

	row.Date, err = time.Parse(_reestryDateFormat, _reestryDatePattern.FindString(date))
	if err != nil {
		return Raw{}, fmt.Errorf("can't parse date %s -> %w", date, err)
	}

	return row, nil
}
