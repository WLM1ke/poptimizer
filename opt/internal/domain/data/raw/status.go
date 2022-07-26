package raw

import (
	"context"
	"encoding/csv"
	"errors"
	"io"
	"net/http"
	"regexp"
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"golang.org/x/text/encoding/charmap"
)

const (
	// _statusGroup группа и id данных об ожидаемых датах выплаты дивидендов.
	_statusGroup = `status`

	_statusURL          = `https://www.moex.com/ru/listing/listing-register-closing-csv.aspx`
	_statusDateFormat   = `02.01.2006 15:04:05`
	_statusLookBackDays = 14
)

var reTicker = regexp.MustCompile(`, ([A-Z]+-[A-Z]+|[A-Z]+) \[`)

// StatusService осуществляющий загрузку информации об ожидаемых датах выплаты дивидендов.
type StatusService struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[StatusTable]
	client *http.Client
}

// NewStatusService создает сервис загрузки информации об ожидаемых датах выплаты дивидендов.
func NewStatusService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[StatusTable],
	client *http.Client,
) *StatusService {
	return &StatusService{
		logger: logger,
		client: client,
		repo:   repo,
	}
}

// Update информацию об ожидаемых датах выплаты дивидендов.
func (s StatusService) Update(ctx context.Context, date time.Time, table securities.Table) StatusTable {
	defer s.logger.Infof("update is finished")

	agg, err := s.repo.Get(ctx, StatusID())
	if err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	rows := s.download(ctx, table)

	if rows.IsEmpty() {
		return nil
	}

	agg.Update(rows, date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	return rows
}

func (s StatusService) download(
	ctx context.Context,
	table securities.Table,
) StatusTable {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _statusURL, http.NoBody)
	if err != nil {
		s.logger.Warnf("can't create request -> %w", err)

		return nil
	}

	resp, err := s.client.Do(request)
	if err != nil {
		s.logger.Warnf("can't make request -> %w", err)

		return nil
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		s.logger.Warnf("bad respond code %s", resp.Status)

		return nil
	}

	decoder := charmap.Windows1251.NewDecoder()
	reader := csv.NewReader(decoder.Reader(resp.Body))

	rows := s.parceCSV(reader, table)

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

	return rows
}

func (s StatusService) parceCSV(
	reader *csv.Reader,
	table securities.Table,
) (rows StatusTable) {
	for header := true; ; {
		record, err := reader.Read()

		switch {
		case errors.Is(err, io.EOF):
			return rows
		case err != nil:
			s.logger.Warnf(
				"can't parse row %s -> %w",
				record,
				err,
			)

			continue
		case header:
			header = false

			continue
		}

		divDate, err := time.Parse(_statusDateFormat, record[1])
		if err != nil {
			s.logger.Warnf(
				"can't parse date %s ->  %w",
				record[1],
				err,
			)

			continue
		}

		if divDate.Before(time.Now().AddDate(0, 0, -_statusLookBackDays)) {
			continue
		}

		ticker := reTicker.FindStringSubmatch(record[0])
		if ticker == nil {
			s.logger.Warnf(
				"can't parse ticker %s",
				record[0],
			)

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
