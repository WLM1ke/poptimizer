package div

import (
	"context"
	"encoding/csv"
	"errors"
	"fmt"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/selected"
	"golang.org/x/text/encoding/charmap"
	"io"
	"net/http"
	"regexp"
	"sort"
	"time"
)

const (
	// StatusGroup группа и id данных об ожидаемых датах выплаты дивидендов.
	StatusGroup = `status`

	_url          = `https://www.moex.com/ru/listing/listing-register-closing-csv.aspx`
	_dateFormat   = `02.01.2006 15:04:05`
	_lookBackDays = 0
)

// Акция со странным тикером nompp не торгуется, но попадает в отчеты.
var reTicker = regexp.MustCompile(`, ([A-Z]+-[A-Z]+|[A-Z]+|nompp) \[`)

// Status - информация об ожидаемых датах выплаты дивидендов.
type Status struct {
	Ticker string
	Date   time.Time
}

// StatusHandler обработчик событий, отвечающий за загрузку информации об ожидаемых датах выплаты дивидендов.
type StatusHandler struct {
	domain.Filter
	pub    domain.Publisher
	repo   domain.ReadWriteRepo[data.Rows[Status]]
	client *http.Client
}

// NewStatusHandler создает обработчик событий, отвечающий за загрузку информации об ожидаемых датах выплаты дивидендов.
func NewStatusHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[data.Rows[Status]],
	client *http.Client,
) *StatusHandler {
	return &StatusHandler{
		Filter: domain.Filter{
			Sub:   data.Subdomain,
			Group: selected.Group,
			ID:    selected.Group,
		},
		client: client,
		repo:   repo,
		pub:    pub,
	}
}

// Handle реагирует на событие об торгуемых бумагах и обновляет информацию об ожидаемых датах выплаты дивидендов.
func (h StatusHandler) Handle(ctx context.Context, event domain.Event) {
	qid := domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: StatusGroup,
		ID:    StatusGroup,
	}

	event.QualifiedID = qid

	selectedTickers, ok := event.Data.(selected.Tickers)
	if !ok {
		event.Data = fmt.Errorf("can't parse event %s data", qid)
		h.pub.Publish(event)

		return
	}

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	raw, err := h.download(ctx, selectedTickers)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	rows := data.Rows[Status](raw)

	if rows.IsEmpty() {
		return
	}

	table.Timestamp = event.Timestamp
	table.Entity = rows

	if err := h.repo.Save(ctx, table); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	h.publish(table)
}

func (h StatusHandler) download(
	ctx context.Context,
	selectedTickers selected.Tickers,
) ([]Status, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _url, http.NoBody)
	if err != nil {
		return nil, fmt.Errorf(
			"can't create request -> %w",
			err,
		)
	}

	resp, err := h.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf(
			"can't make request -> %w",
			err,
		)
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf(
			"bad respond repo %s",
			resp.Status,
		)
	}

	decoder := charmap.Windows1251.NewDecoder()
	reader := csv.NewReader(decoder.Reader(resp.Body))

	rows, err := h.parceCSV(reader, selectedTickers)
	if err != nil {
		return nil, err
	}

	sort.Slice(
		rows,
		func(i, j int) bool {
			switch {
			case rows[i].Ticker < rows[j].Ticker:
				return true
			case (rows[i].Ticker == rows[j].Ticker) && rows[i].Date.Before(rows[j].Date):
				return true
			default:
				return false
			}
		},
	)

	return rows, nil
}

func (h StatusHandler) parceCSV(
	reader *csv.Reader,
	selectedTickers selected.Tickers,
) (rows []Status, err error) {
	header := true

	if err != nil {
		return nil, err
	}

	for {
		record, err := reader.Read()
		switch {
		case errors.Is(err, io.EOF):
			return rows, nil
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

		if divDate.Before(time.Now().AddDate(0, 0, -_lookBackDays)) {
			continue
		}

		ticker := reTicker.FindStringSubmatch(record[0])
		if ticker == nil {
			return nil, fmt.Errorf(
				"can't parse ticker %s",
				record[0],
			)
		}

		if selectedTickers[ticker[1]] {
			rows = append(rows, Status{
				Ticker: ticker[1],
				Date:   divDate,
			})
		}
	}
}

func (h StatusHandler) publish(table domain.Aggregate[data.Rows[Status]]) {
	for _, div := range table.Entity {
		h.pub.Publish(domain.Event{
			QualifiedID: domain.QualifiedID{
				Sub:   data.Subdomain,
				Group: StatusGroup,
				ID:    div.Ticker,
			},
			Timestamp: table.Timestamp,
			Data:      div,
		})
	}
}
