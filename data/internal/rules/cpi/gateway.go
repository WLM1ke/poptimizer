package cpi

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/xuri/excelize/v2"
	"net/http"
	"strconv"
	"time"
)

const (
	_url   = `https://rosstat.gov.ru/storage/mediabank/i_ipc_1991-2021.xlsx`
	_sheet = `ИПЦ`

	_headerRow = 3
	_firstYear = 1991

	_firstDataRow = 5
	_firstDataCol = 1
)

var _months = [12]string{
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

type gateway struct {
	client *http.Client
}

func (g gateway) Get(ctx context.Context, table domain.Table[CPI], _ time.Time) ([]CPI, error) {
	xlsx, err := g.getXLSX(ctx)
	if err != nil {
		return nil, err
	}

	rows, err := xlsx.GetRows(_sheet, excelize.Options{RawCellValue: true})
	if err != nil {
		return nil, err
	}

	err = validateMonths(rows)
	if err != nil {
		return nil, err
	}

	years, err := getYears(rows[_headerRow][_firstDataCol:])
	if err != nil {
		return nil, err
	}

	cpi, err := parsedData(years, rows[_firstDataRow:_firstDataRow+12])
	switch {
	case err != nil:
		return nil, err
	case table.IsEmpty():
		return cpi, nil
	case table.LastRow().Date.Before(cpi[len(cpi)-1].Date):
		return cpi, nil
	default:
		return nil, nil
	}
}

func (g gateway) getXLSX(ctx context.Context) (*excelize.File, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _url, http.NoBody)
	if err != nil {
		return nil, err
	}

	resp, err := g.client.Do(request)
	if err != nil {
		return nil, err
	}

	defer resp.Body.Close()


	if resp.StatusCode != http.StatusOK {
		return nil,  fmt.Errorf(
			"%w: bad respond status %s",
			template.ErrRuleGateway,
			resp.Status,
		)
	}


	return excelize.OpenReader(resp.Body)
}

func validateMonths(rows [][]string) error {
	for n, month := range _months {
		if rows[_firstDataRow+n][0] != month {
			return fmt.Errorf(
				"%w: wrong month name %s vs %s",
				template.ErrRuleGateway,
				rows[_firstDataRow+n][0],
				month,
			)
		}
	}

	return nil
}

func getYears(header []string) ([]int, error) {
	years := make([]int, 0, 64)

	for n, value := range header {
		year, err := strconv.Atoi(value)
		if err != nil {
			return nil, err
		}

		if year != _firstYear+n {
			return nil, fmt.Errorf(
				"%w: wrong year %d vs %d",
				template.ErrNewRowsValidation,
				year,
				_firstYear+n,
			)
		}

		years = append(years, year)
	}

	return years, nil
}

func parsedData(years []int, data [][]string) ([]CPI, error) {
	cpi := make([]CPI, 0, 1024)

	for col, year := range years {
		for month := 0; month < 12; month++ {
			if len(data[month]) == _firstDataCol+col {
				return cpi, nil
			}

			value, err := strconv.ParseFloat(data[month][_firstDataCol+col], 64)
			if err != nil {
				return nil, err
			}

			cpi = append(cpi, CPI{
				Date:  lastDayOfMonth(year, month),
				Close: value / 100.0,
			})
		}
	}

	return cpi, nil
}

func lastDayOfMonth(year int, month int) time.Time {
	date := time.Date(year, time.Month(month+2), 1, 0, 0, 0, 0, time.UTC)

	return date.AddDate(0, 0, -1)
}
