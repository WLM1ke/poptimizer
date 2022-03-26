package edit

import (
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

const _timeFormat = "2006-01-02"

func parseForm(r *http.Request) (domain.RawDiv, error) {
	if err := r.ParseForm(); err != nil {
		return domain.RawDiv{}, err
	}

	if len(r.PostForm) != 3 {
		return domain.RawDiv{}, fmt.Errorf("expected 3 keys got %d", len(r.PostForm))
	}

	return parseRow(r.PostForm)
}

func parseRow(form url.Values) (row domain.RawDiv, err error) {
	for key, value := range form {
		if len(value) > 1 {
			return row, fmt.Errorf("expected 1 value got %d", len(value))
		}

		switch key {
		case "date":
			var err error
			row.Date, err = time.Parse(_timeFormat, value[0])

			if err != nil {
				return row, err
			}
		case "value":
			var err error
			row.Value, err = strconv.ParseFloat(value[0], 64)

			if err != nil {
				return row, err
			}
		case "currency":
			row.Currency = value[0]
		default:
			return row, fmt.Errorf("unknown key %s", key)
		}
	}

	return row, nil
}
