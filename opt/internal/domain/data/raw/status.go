package raw

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

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"golang.org/x/text/encoding/charmap"
)

const (
	// _statusGroup группа и id данных об ожидаемых датах выплаты дивидендов.
	_statusGroup = `status`

	_statusURL          = `https://www.moex.com/ru/listing/listing-register-closing-csv.aspx`
	_statusDateFormat   = `02.01.2006 15:04:05`
	_statusLookBackDays = 0
)

// Акция со странным тикером nompp не торгуется, но попадает в отчеты.
var reTicker = regexp.MustCompile(`, ([A-Z]+-[A-Z]+|[A-Z]+|nompp) \[`)

// StatusHandler обработчик событий, отвечающий за загрузку информации об ожидаемых датах выплаты дивидендов.
type StatusHandler struct {
	pub    domain.Publisher
	repo   domain.ReadWriteRepo[StatusTable]
	client *http.Client
}

// NewStatusHandler создает обработчик событий, отвечающий за загрузку информации об ожидаемых датах выплаты дивидендов.
func NewStatusHandler(
	pub domain.Publisher,
	repo domain.ReadWriteRepo[StatusTable],
	client *http.Client,
) *StatusHandler {
	return &StatusHandler{
		client: client,
		repo:   repo,
		pub:    pub,
	}
}

// Match выбирает событие с обновлением перечня торгуемых бумаг.
func (h StatusHandler) Match(event domain.Event) bool {
	_, ok := event.Data.(securities.Table)

	return ok && securities.GroupID() == event.QID
}

func (h StatusHandler) String() string {
	return "securities -> dividend status"
}

// Handle реагирует на событие об выбранных бумагах и обновляет информацию об ожидаемых датах выплаты дивидендов.
func (h StatusHandler) Handle(ctx context.Context, event domain.Event) {
	sec, ok := event.Data.(securities.Table)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := StatusID(_statusGroup)

	event.QID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	rows, errs := h.download(ctx, sec)
	if len(errs) > 0 {
		for _, err := range errs {
			event.Data = err
			h.pub.Publish(event)
		}
	}

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
	table securities.Table,
) (StatusTable, []error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _statusURL, http.NoBody)
	if err != nil {
		return nil, []error{fmt.Errorf(
			"can't create request -> %w",
			err,
		)}
	}

	resp, err := h.client.Do(request)
	if err != nil {
		return nil, []error{fmt.Errorf(
			"can't make request -> %w",
			err,
		)}
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, []error{fmt.Errorf(
			"bad respond repo %s",
			resp.Status,
		)}
	}

	decoder := charmap.Windows1251.NewDecoder()
	reader := csv.NewReader(decoder.Reader(resp.Body))

	rows, errs := h.parceCSV(reader, table)

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

	return rows, errs
}

func (h StatusHandler) parceCSV(
	reader *csv.Reader,
	table securities.Table,
) (rows StatusTable, errs []error) {
	for header := true; ; {
		record, err := reader.Read()

		switch {
		case errors.Is(err, io.EOF):
			return rows, errs
		case err != nil:
			errs = append(errs, fmt.Errorf(
				"can't parse row %s -> %w",
				record,
				err,
			))

			continue
		case header:
			header = false

			continue
		}

		divDate, err := time.Parse(_statusDateFormat, record[1])
		if err != nil {
			errs = append(errs, fmt.Errorf(
				"can't parse date %s ->  %w",
				record[1],
				err,
			))

			continue
		}

		if divDate.Before(time.Now().AddDate(0, 0, -_statusLookBackDays)) {
			continue
		}

		ticker := reTicker.FindStringSubmatch(record[0])
		if ticker == nil {
			errs = append(errs, fmt.Errorf(
				"can't parse ticker %s",
				record[0],
			))

			continue
		}

		if sec, ok := table.Get(ticker[1]); sec.Selected && ok {
			rows = append(rows, Status{
				Ticker:     ticker[1],
				BaseTicker: sec.BaseTicker(),
				Preferred:  sec.IsPreferred(),
				Foreign:    sec.IsForeign(),
				Date:       divDate,
			})
		}
	}
}

func (h StatusHandler) publish(table domain.Aggregate[StatusTable]) {
	for _, div := range table.Entity {
		h.pub.Publish(domain.Event{
			QID:       StatusID(div.Ticker),
			Timestamp: table.Timestamp,
			Data:      div,
		})
	}
}
