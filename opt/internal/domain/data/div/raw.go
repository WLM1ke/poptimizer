package div

import (
	"context"
	"fmt"
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"sort"
	"time"
)

const (
	// RawGroup группа и id введенных пользователем дивидендов.
	RawGroup = `raw_div`
	// USDCurrency - наименование валюты доллара.
	USDCurrency = `USD`
	// RURCurrency - наименование валюты рубля.
	RURCurrency = `RUR`

	_format = `2006-01-02`
)

// Raw представляет дивиденды не конвертированные в валюту расчетов.
type Raw struct {
	Date     time.Time
	Value    float64
	Currency string
}

// CheckRawHandler обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
type CheckRawHandler struct {
	domain.Filter
	pub  domain.Publisher
	repo domain.ReadRepo[data.Rows[Raw]]
	iss  *gomoex.ISSClient
}

// NewCheckRawHandler новый обработчик событий, отвечающий за проверку актуальности введенных пользователем дивидендов.
func NewCheckRawHandler(
	pub domain.Publisher,
	repo domain.ReadRepo[data.Rows[Raw]],

) *CheckRawHandler {
	return &CheckRawHandler{
		Filter: domain.Filter{
			Sub:   data.Subdomain,
			Group: StatusGroup,
		},
		repo: repo,
		pub:  pub,
	}
}

// Handle реагирует на событие об обновлении статуса дивидендов и проверяет пользовательские дивиденды.
func (h CheckRawHandler) Handle(ctx context.Context, event domain.Event) {
	status, ok := event.Data.(Status)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := domain.QualifiedID{
		Sub:   data.Subdomain,
		Group: RawGroup,
		ID:    event.ID,
	}

	event.QualifiedID = qid

	table, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}
	n := sort.Search(
		len(table.Entity),
		func(i int) bool { return !table.Entity[i].Date.Before(status.Date) },
	)

	if (n == len(table.Entity)) || !status.Date.Equal(table.Entity[n].Date) {
		event.Data = fmt.Errorf(
			"%s missed dividend at %s",
			event.ID,
			status.Date.Format(_format),
		)
		h.pub.Publish(event)
	}
}
