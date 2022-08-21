package cpi

import (
	"context"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"github.com/xuri/excelize/v2"
)

const (
	_URL = `https://rosstat.gov.ru/storage/mediabank/ipc_4(2).xlsx`

	_sheet = `01`

	_headerRow = 3
	_firstYear = 1991

	_firstDataRow = 5
	_firstDataCol = 1
)

// Service загружает данные по инфляции.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	client *http.Client
}

// NewService создает новый загрузчик данных по инфляции.
func NewService(logger lgr.Logger, repo domain.ReadWriteRepo[Table], client *http.Client) *Service {
	return &Service{logger: logger, repo: repo, client: client}
}

// Update загружает данные по инфляции.
func (s Service) Update(ctx context.Context, date time.Time) {
	defer s.logger.Infof("update is finished")

	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	rows, err := s.download(ctx)
	if err != nil {
		s.logger.Warnf("%s %s", ID(), err)

		return
	}

	switch haveNewRows, err := s.validate(agg.Entity(), rows); {
	case err != nil:
		s.logger.Warnf("%s %s", ID(), err)

		return
	case !haveNewRows:
		return
	}

	agg.Update(rows, date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s %s", ID(), err)

		return
	}
}

func (s Service) download(ctx context.Context) (Table, error) {
	xlsx, err := s.getXLSX(ctx)
	if err != nil {
		return nil, err
	}

	rows, err := xlsx.GetRows(_sheet, excelize.Options{RawCellValue: true})
	if err != nil {
		return nil, fmt.Errorf(
			"can't extract rows -> %w",
			err,
		)
	}

	err = validateMonths(rows)
	if err != nil {
		return nil, err
	}

	years, err := getYears(rows[_headerRow][_firstDataCol:])
	if err != nil {
		return nil, err
	}

	return parsedData(years, rows[_firstDataRow:_firstDataRow+12])
}

func (s Service) getXLSX(ctx context.Context) (*excelize.File, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _URL, http.NoBody)
	if err != nil {
		return nil, fmt.Errorf(
			"can't create request -> %w",
			err,
		)
	}

	resp, err := s.client.Do(request)
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

	reader, err := excelize.OpenReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf(
			"can't parse xlsx -> %w",
			err,
		)
	}

	return reader, nil
}

func validateMonths(rows [][]string) error {
	months := [12]string{
		`январь`,
		`февраль`,
		`март`,
		`апрель`,
		`май`,
		`июнь`,
		`июль`,
		`август`,
		`сентябрь`,
		`октябрь`,
		`ноябрь`,
		`декабрь`,
	}
	for n, month := range months {
		if rows[_firstDataRow+n][0] != month {
			return fmt.Errorf(
				"wrong month name %s vs %s",
				rows[_firstDataRow+n][0],
				month,
			)
		}
	}

	return nil
}

func getYears(header []string) ([]int, error) {
	years := make([]int, 0, len(header))

	for position, value := range header {
		year, err := strconv.Atoi(value)
		if err != nil {
			return nil, fmt.Errorf(
				"can't parse -> %w",
				err,
			)
		}

		if year != _firstYear+position {
			return nil, fmt.Errorf(
				"wrong year %d vs %d",
				year,
				_firstYear+position,
			)
		}

		years = append(years, year)
	}

	return years, nil
}

func parsedData(years []int, data [][]string) (Table, error) {
	monthsInYear := 12
	cpi := make(Table, 0, monthsInYear*len(years))

	for col, year := range years {
		for month := 0; month < monthsInYear; month++ {
			if len(data[month]) == _firstDataCol+col {
				return cpi, nil
			}

			percents, err := strconv.ParseFloat(data[month][_firstDataCol+col], 64)
			if err != nil {
				return nil, fmt.Errorf(
					"can't parse -> %w",
					err,
				)
			}

			cpi = append(cpi, CPI{
				Date:  lastDayOfMonth(year, month),
				Value: percents / 100, //nolint:gomnd
			})
		}
	}

	return cpi, nil
}

func lastDayOfMonth(year, month int) time.Time {
	afterFullMonth := 2
	date := time.Date(year, time.Month(month+afterFullMonth), 1, 0, 0, 0, 0, time.UTC)

	return date.AddDate(0, 0, -1)
}

func (s Service) validate(table, rows Table) (bool, error) {
	if len(table) > len(rows) {
		return false, fmt.Errorf("too few cpi rows %d < %d", len(rows), len(table))
	}

	for num, row := range table {
		if row != rows[num] {
			return false, fmt.Errorf(
				"old row %+v not match new %+v",
				row,
				rows[num],
			)
		}
	}

	return len(table) < len(rows), nil
}
