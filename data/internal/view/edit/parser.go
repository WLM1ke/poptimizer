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

func parseForm(r *http.Request) (id string, row domain.RawDiv, err error) {
	if err := r.ParseForm(); err != nil {
		return id, row, err
	}

	if len(r.PostForm) != 4 {
		return id, row, fmt.Errorf("expected 4 keys got %d", len(r.PostForm))
	}

	return parseRow(r.PostForm)
}

func parseRow(form url.Values) (id string, row domain.RawDiv, err error) {
	for key, value := range form {
		if len(value) > 1 {
			return id, row, fmt.Errorf("expected 1 value got %d", len(value))
		}

		switch key {
		case "id":
			id = value[0]
		case "date":
			var err error
			row.Date, err = time.Parse(_timeFormat, value[0])

			if err != nil {
				return id, row, err
			}
		case "value":
			var err error
			row.Value, err = strconv.ParseFloat(value[0], 64)

			if err != nil {
				return id, row, err
			}
		case "currency":
			row.Currency = value[0]
		default:
			return id, row, fmt.Errorf("unknown key %s", key)
		}
	}

	return id, row, nil
}
