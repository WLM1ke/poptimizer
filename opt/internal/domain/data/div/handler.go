package div

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/usd"
)

// Handler обработчик событий, для обновления дивидендов в рублях.
type Handler struct {
	pub  domain.Publisher
	repo domain.ReadWriteRepo[Table]
	raw  domain.ReadRepo[raw.Table]
}

// NewHandler создает обработчик событий, для обновления дивидендов в рублях.
func NewHandler(pub domain.Publisher, repo domain.ReadWriteRepo[Table], rawDiv domain.ReadRepo[raw.Table]) *Handler {
	return &Handler{pub: pub, repo: repo, raw: rawDiv}
}

// Match выбирает событие о торгуемой бумаге с дополнительно информации о курсе.
func (h Handler) Match(event domain.Event) bool {
	_, ok := event.Data.(usd.Table)

	return ok && event.QID == securities.ID(event.ID)
}

func (h Handler) String() string {
	return "security -> dividends"
}

// Handle реагирует на событие об торгуемой бумаге и обновляет ее дивиденды в рублях.
func (h Handler) Handle(ctx context.Context, event domain.Event) {
	rates, ok := event.Data.(usd.Table)
	if !ok {
		event.Data = fmt.Errorf("can't parse %s data", event)
		h.pub.Publish(event)

		return
	}

	qid := ID(event.ID)

	event.QID = qid

	rawDiv, err := h.raw.Get(ctx, raw.ID(event.ID))
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if len(rawDiv.Entity) == 0 {
		return
	}

	div, err := h.prepareDiv(rawDiv.Entity, rates)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	if err := h.validate(div); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	agg, err := h.repo.Get(ctx, qid)
	if err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}

	agg.Timestamp = event.Timestamp
	agg.Entity = div

	if err := h.repo.Save(ctx, agg); err != nil {
		event.Data = err
		h.pub.Publish(event)

		return
	}
}

func (h Handler) prepareDiv(
	rawDivs raw.Table,
	rates usd.Table,
) (dividends Table, err error) {
	var date time.Time

	for _, row := range rawDivs {
		if !row.Date.Equal(date) {
			date = row.Date

			dividends = append(dividends, Dividend{Date: date})
		}

		switch row.Currency {
		case raw.RURCurrency:
			dividends[len(dividends)-1].Value += row.Value
		case raw.USDCurrency:
			n := sort.Search(
				len(rates),
				func(i int) bool { return rates[i].Date.After(date) },
			)
			dividends[len(dividends)-1].Value += row.Value * rates[n-1].Close
		default:
			return nil, fmt.Errorf(
				"unknown currency %+v",
				row.Currency,
			)
		}
	}

	return dividends, nil
}

func (h Handler) validate(div Table) error {
	prev := div[0].Date
	for _, row := range div[1:] {
		if prev.Before(row.Date) {
			prev = row.Date

			continue
		}

		return fmt.Errorf("not increasing dates %+v and %+v", prev, row.Date)
	}

	return nil
}
