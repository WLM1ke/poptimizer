package raw

import (
	"context"
	"sort"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
)

const (
	_extra  = "extra"
	_ok     = "ok"
	_missed = "missed"
)

// Service сервис для работы с введенными вручную дивидендами.
type Service struct {
	sec domain.ReadRepo[securities.Table]
	raw domain.ReadWriteRepo[Table]
	pub domain.Publisher
}

// NewService создает новый сервис для работы с введенными вручную дивидендами.
func NewService(
	sec domain.ReadRepo[securities.Table],
	raw domain.ReadWriteRepo[Table],
	pub domain.Publisher,
) *Service {
	return &Service{sec: sec, raw: raw, pub: pub}
}

// TickersDTO содержит сортированный перечень тикеров.
type TickersDTO []string

// GetTickers выдает информацию о доступных тикерах.
func (s Service) GetTickers(ctx context.Context) (TickersDTO, domain.ServiceError) {
	agg, err := s.sec.Get(ctx, securities.GroupID())
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	tickers := make(TickersDTO, len(agg.Entity))

	for n, sec := range agg.Entity {
		tickers[n] = sec.Ticker
	}

	return tickers, nil
}

// DividendsDTO содержит информацию о дивидендах и их статусе.
type DividendsDTO []divRow

type divRow struct {
	Date     time.Time `json:"date"`
	Value    float64   `json:"value"`
	Currency string    `json:"currency"`
	Status   string    `json:"status"`
}

// GetDividends получает сводную информацию о дивидендах по указанному тикеру.
//
// Кроме самих о дивидендах содержится информация об их статусе - пропусках или наличии дополнительных по сравнению с
// источниками в интернете.
func (s Service) GetDividends(ctx context.Context, ticker string) (DividendsDTO, domain.ServiceError) {
	allSec, err := s.sec.Get(ctx, securities.GroupID())
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	sec, ok := allSec.Entity.Get(ticker)
	if !ok {
		return nil, domain.NewBadServiceRequestErr("wrong ticker %s", ticker)
	}

	raw, err := s.raw.Get(ctx, ID(ticker))
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	qid := CloseReestryID(ticker)

	if sec.IsForeign() {
		qid = NasdaqID(ticker)
	}

	source, err := s.raw.Get(ctx, qid)
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	dto := mergeWithSource(raw.Entity, source.Entity)

	return dto, nil
}

func mergeWithSource(raw, source Table) DividendsDTO {
	dto := make(DividendsDTO, 0, len(raw))

	for _, div := range raw {
		status := _ok
		if !source.Exists(div) {
			status = _extra
		}

		dto = append(dto, divRow{Date: div.Date, Value: div.Value, Currency: div.Currency, Status: status})
	}

	for _, div := range source {
		if div.ValidDate() && !raw.Exists(div) {
			dto = append(dto, divRow{Date: div.Date, Value: div.Value, Currency: div.Currency, Status: _missed})
		}
	}

	sort.Slice(dto, func(i, j int) bool {
		return dto[i].Date.Before(dto[j].Date)
	})

	return dto
}

// SaveDividendsDTO содержит информацию об измененных дивидендах.
type SaveDividendsDTO struct {
	Ticker    string `json:"ticker"`
	Dividends []Raw  `json:"dividends"`
}

func (d SaveDividendsDTO) validate() domain.ServiceError {
	for _, row := range d.Dividends {
		if tz, offset := row.Date.Zone(); offset != 0 {
			return domain.NewBadServiceRequestErr("not UTC timezone %s", tz)
		}

		dateOnly := time.Date(
			row.Date.Year(),
			row.Date.Month(),
			row.Date.Day(),
			0,
			0,
			0,
			0,
			time.UTC,
		)
		if !row.Date.Equal(dateOnly) {
			return domain.NewBadServiceRequestErr("wrong date %s", row.Date)
		}

		if row.Value < 0 {
			return domain.NewBadServiceRequestErr("dividends must be positive %f", row.Value)
		}

		if row.Currency != USDCurrency && row.Currency != RURCurrency {
			return domain.NewBadServiceRequestErr("unknown currency %s", row.Currency)
		}
	}

	return nil
}

// Save сохраняет измененные дивиденды.
func (s Service) Save(ctx context.Context, dto SaveDividendsDTO) domain.ServiceError {
	if err := dto.validate(); err != nil {
		return err
	}

	ticker := dto.Ticker

	allSec, err := s.sec.Get(ctx, securities.GroupID())
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	_, ok := allSec.Entity.Get(ticker)
	if !ok {
		return domain.NewBadServiceRequestErr("ticker %s doesn't exist", ticker)
	}

	agg, err := s.raw.Get(ctx, ID(ticker))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	agg.Entity = dto.Dividends

	agg.Entity.Sort()

	if err := s.raw.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	s.pub.Publish(domain.Event{
		QualifiedID: ID(ticker),
		Timestamp:   agg.Timestamp,
	})

	return nil
}
