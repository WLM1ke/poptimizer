package div

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

// CheckCloseReestryHandler обработчик событий, отвечающий за проверку дивидендов на закрытияреестров.рф.
type CheckCloseReestryHandler struct {
	pub    domain.Publisher
	repo   domain.ReadWriteRepo[RawTable]
	client *http.Client
}

// NewCheckCloseReestryHandler новый обработчик событий, отвечающий за проверку дивидендов с закрытияреестров.рф.
func NewCheckCloseReestryHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[RawTable],
	client *http.Client,
) *CheckCloseReestryHandler {
	return &CheckCloseReestryHandler{
		repo:   repo,
		pub:    pub,
		client: client,
	}
}

// Match выбирает события изменения статуса дивидендов по не иностранным тикерам.
func (h CheckCloseReestryHandler) Match(event domain.Event) bool {
	status, ok := event.Data.(Status)

	return ok && !status.Foreign && event.QualifiedID == StatusID(event.ID)
}

func (h CheckCloseReestryHandler) String() string {
	return "dividend status not foreign -> check close reestry"
}

// Handle реагирует на событие об обновлении статуса дивидендов и обновляет дивиденды с закрытияреестров.рф.
func (h CheckCloseReestryHandler) Handle(ctx context.Context, event domain.Event) { //nolint:dupl
	status, ok := event.Data.(Status)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := CloseReestryID(event.ID)

	event.QualifiedID = qid

	agg, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if agg.Entity.ExistsDate(status.Date) {
		return
	}

	table, err := h.download(ctx, status)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	table.Sort()

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

func (h CheckCloseReestryHandler) download(ctx context.Context, status Status) (RawTable, error) {
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		makeURL(status),
		http.NoBody,
	)
	if err != nil {
		return nil, fmt.Errorf("can't prepare CloseReestry request for %s -> %w", status.Ticker, err)
	}

	respond, err := h.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("can't get CloseReestry respond for %s -> %w", status.Ticker, err)
	}

	defer respond.Body.Close()

	if respond.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get CloseReestry status %s for %s", respond.Status, status.Ticker)
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

func parseRequest(respond *http.Response, preferred bool) (RawTable, error) {
	html, err := goquery.NewDocumentFromReader(respond.Body)
	if err != nil {
		return nil, fmt.Errorf("can't parse CloseReestry html -> %w", err)
	}

	table := html.Find("tbody").Find("tr")

	if err := validateHeader(table, preferred); err != nil {
		return nil, err
	}

	nodes := table.Slice(1, goquery.ToEnd).Nodes
	rows := make(RawTable, 0, len(nodes))

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

func parseRow(htmlRow *goquery.Document, preferred bool) (row Raw, err error) {
	date := htmlRow.Find("td:nth-child(1)").Text()

	row.Date, err = time.Parse(_reestryDateFormat, _reestryDatePattern.FindString(date))
	if err != nil {
		return Raw{}, fmt.Errorf("can't parse date %s -> %w", date, err)
	}

	valueStr := htmlRow.Find("td:nth-child(2)").Text()
	if preferred {
		valueStr = htmlRow.Find("td:nth-child(3)").Text()
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

	return row, nil
}
