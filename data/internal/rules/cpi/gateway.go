package cpi

import (
	"context"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"
	"strconv"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/xuri/excelize/v2"
	"golang.org/x/text/encoding/charmap"
)

const (
	_pricesURL = `https://rosstat.gov.ru/price`
	_cpiHost   = `https://rosstat.gov.ru`

	_sheet = `ИПЦ`

	_headerRow = 3
	_firstYear = 1991

	_firstDataRow = 5
	_firstDataCol = 1
)

var (
	_cpiPathRE = regexp.MustCompile(`/storage/mediabank/ind_potreb_cen_.+html`)
	_urlRE     = regexp.MustCompile(`https://rosstat\.gov\.ru/.+ipc.+xlsx`)
)

type gateway struct {
	client *http.Client
}

func (g gateway) Get(ctx context.Context, table domain.Table[domain.CPI]) ([]domain.CPI, error) {
	xlsx, err := g.getXLSX(ctx)
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
	url, err := g.getURL(ctx)
	if err != nil {
		return nil, err
	}

	request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, http.NoBody)
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

	reader, err := excelize.OpenReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf(
			"can't parse xlsx -> %w",
			err,
		)
	}

	return reader, nil
}

func (g gateway) makeCPIPageURL(ctx context.Context) (string, error) {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, _pricesURL, http.NoBody)
	if err != nil {
		return "", fmt.Errorf(
			"can't create request -> %w",
			err,
		)
	}

	resp, err := g.client.Do(request)
	if err != nil {
		return "", fmt.Errorf(
			"can't make request -> %w",
			err,
		)
	}

	defer resp.Body.Close()

	page, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf(
			"can't read prices page -> %w",
			err,
		)
	}

	return fmt.Sprintf("%s%s", _cpiHost, _cpiPathRE.Find(page)), nil
}

func (g gateway) getURL(ctx context.Context) (string, error) {
	url, err := g.makeCPIPageURL(ctx)
	if err != nil {
		return "", err
	}

	request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, http.NoBody)
	if err != nil {
		return "", fmt.Errorf(
			"can't create request -> %w",
			err,
		)
	}

	resp, err := g.client.Do(request)
	if err != nil {
		return "", fmt.Errorf(
			"can't make request -> %w",
			err,
		)
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf(
			"bad respond status %s",
			resp.Status,
		)
	}

	decoder := charmap.Windows1252.NewDecoder()
	reader := decoder.Reader(resp.Body)

	page, err := ioutil.ReadAll(reader)
	if err != nil {
		return "", fmt.Errorf(
			"can't decode cp1252 -> %w",
			err,
		)
	}

	return string(_urlRE.Find(page)), nil
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

func parsedData(years []int, data [][]string) ([]domain.CPI, error) {
	monthsInYear := 12
	cpi := make([]domain.CPI, 0, monthsInYear*len(years))

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

			cpi = append(cpi, domain.CPI{
				Date:  lastDayOfMonth(year, month),
				Value: percents / 100, //nolint:gomnd
			})
		}
	}

	return cpi, nil
}

func lastDayOfMonth(year int, month int) time.Time {
	afterFullMonth := 2
	date := time.Date(year, time.Month(month+afterFullMonth), 1, 0, 0, 0, 0, time.UTC)

	return date.AddDate(0, 0, -1)
}
