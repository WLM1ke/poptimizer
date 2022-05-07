package services

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

const _timeFormat = "2006-01-02"

// RawDivInfo представление информации о редактируемых дивидендах.
type RawDivInfo struct {
	Ticker    string
	Dividends []domain.CurrencyDiv
	source    []domain.CurrencyDiv
}

func (d RawDivInfo) Missed() (missed []domain.CurrencyDiv) {
	index := make(map[domain.CurrencyDiv]bool)

	for _, row := range d.Dividends {
		index[row] = true
	}

	for _, row := range d.source {
		if row.Date.After(domain.FirstDividendDate()) && !index[row] {
			missed = append(missed, row)
		}
	}

	return missed
}

// NewDiv шаблон для создания новой записи о дивидендах.
func (d RawDivInfo) NewDiv() domain.CurrencyDiv {
	if missed := d.Missed(); len(missed) > 0 {
		return missed[0]
	}

	if len(d.Dividends) > 0 {
		return d.Dividends[len(d.Dividends)-1]
	}

	return domain.CurrencyDiv{
		Date:     time.Now(),
		Value:    1,
		Currency: domain.RURCurrency,
	}
}

// RawDivEdit - сервис, обрабатывающая запросы по изменению таблицы с дивидендами.
//
// Позволяет загрузить существующую таблицу с данными и создать соответсвующую пользовательскую сессию по
// редактированию. Добавлять новые строки, сбрасывать и сохранять изменения в рамках пользовательской сессии.
type RawDivEdit struct {
	logger *lgr.Logger

	dividends  repo.ReadWrite[domain.CurrencyDiv]
	securities repo.ReadWrite[domain.Security]

	lock sync.Mutex

	id  string
	sec []string
	div RawDivInfo

	bus *bus.EventBus
}

// NewRawDivEdit инициализирует сервис ручного ввода дивидендов.
func NewRawDivEdit(logger *lgr.Logger, db *mongo.Database, eventBus *bus.EventBus) *RawDivEdit {
	return &RawDivEdit{
		logger:     logger,
		dividends:  repo.NewMongo[domain.CurrencyDiv](db),
		securities: repo.NewMongo[domain.Security](db),
		bus:        eventBus,
	}
}

// StartSession инициализирует сессию по редактированию дивидендов.
func (r *RawDivEdit) StartSession(ctx context.Context, sessionID string) error {
	sec, err := r.securities.Get(ctx, domain.NewSecuritiesID())
	if err != nil {
		return fmt.Errorf("can't load securities -> %w", err)
	}

	r.lock.Lock()
	defer r.lock.Unlock()

	r.id = sessionID

	for _, security := range sec.Rows() {
		r.sec = append(r.sec, security.Ticker)
	}

	return nil
}

// FindTicker возвращает перечень существующих тикеров, начинающихся с указанных букв.
func (r *RawDivEdit) FindTicker(sessionID, prefix string) ([]string, error) {
	r.lock.Lock()
	defer r.lock.Unlock()

	if r.id != sessionID {
		return nil, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if prefix == "" {
		return nil, nil
	}

	prefix = strings.ToUpper(prefix)

	var (
		found []string
		end   bool
	)

	for _, ticker := range r.sec {
		if strings.HasPrefix(ticker, prefix) {
			found = append(found, ticker)
			end = true

			continue
		}

		if end {
			break
		}
	}

	return found, nil
}

// GetDividends - возвращает сохраненные данные и создает пользовательскую сессию.
func (r *RawDivEdit) GetDividends(ctx context.Context, sessionID, ticker string) (RawDivInfo, error) {
	raw, err := r.dividends.Get(ctx, domain.NewRawDivID(ticker))
	if err != nil {
		return RawDivInfo{}, fmt.Errorf(
			"can't load raw dividends from dividends -> %w",
			err,
		)
	}

	id := domain.NewReestryDivID(ticker)
	if domain.IsForeignTicker(ticker) {
		id = domain.NewNASDAQDivID(ticker)
	}

	source, err := r.dividends.Get(ctx, id)
	if err != nil {
		return RawDivInfo{}, fmt.Errorf(
			"can't load source dividends from dividends -> %w",
			err,
		)
	}

	r.lock.Lock()
	defer r.lock.Unlock()

	if sessionID != r.id {
		return r.div, fmt.Errorf(
			"wrong session id - %s",
			sessionID,
		)
	}

	r.div = RawDivInfo{
		Ticker:    ticker,
		Dividends: raw.Rows(),
		source:    source.Rows(),
	}

	return r.div, nil
}

//// AddRow добавляет новые строки в таблицу в рамках пользовательской сессии.
// func (r *RawDivEdit) AddRow(sessionID, date, value, currency string) (RawDivInfo, error) {
//	r.lock.Lock()
//	defer r.lock.Unlock()
//
//	if sessionID != r.div.SessionID {
//		return r.div, fmt.Errorf(
//			"wrong session id - %s",
//			sessionID,
//		)
//	}
//
//	row, err := parseRow(date, value, currency)
//	if err != nil {
//		return r.div, err
//	}
//
//	r.div.Dividends = append(r.div.Dividends, row)
//
//	return r.div, nil
//}
//
// func parseRow(date, value, currency string) (row domain.CurrencyDiv, err error) {
//	row.Date, err = time.Parse(_timeFormat, date)
//	if err != nil {
//		return row, fmt.Errorf(
//			"can't parse -> %w",
//			err,
//		)
//	}
//
//	row.Value, err = strconv.ParseFloat(value, 64)
//	if err != nil {
//		return row, fmt.Errorf(
//			"can't parse -> %w",
//			err,
//		)
//	}
//
//	row.Currency = currency
//	if currency != domain.USDCurrency && currency != domain.RURCurrency {
//		return row, fmt.Errorf(
//			"incorrect currency - %s",
//			currency,
//		)
//	}
//
//	return row, nil
//}
//
//// Save сохраняет результаты редактирования.
//func (r *RawDivEdit) Save(ctx context.Context, sessionID string) error {
//	r.lock.Lock()
//	defer r.lock.Unlock()
//
//	defer func() { r.div.SessionID = "" }()
//
//	if sessionID != r.div.SessionID {
//		return fmt.Errorf(
//			"wrong session id - %s",
//			sessionID,
//		)
//	}
//
//	tableID := domain.NewRawDivID(r.div.Ticker)
//
//	rows := r.div.Dividends
//	sort.Slice(rows, func(i, j int) bool { return rows[i].Date.Before(rows[j].Date) })
//
//	err := r.dividends.Replace(ctx, domain.NewTable(tableID, time.Now(), rows))
//	if err != nil {
//		return fmt.Errorf("can't save to dividends -> %w", err)
//	}
//
//	err = r.bus.Send(domain.NewUpdateCompleted(tableID))
//	if err != nil {
//		return fmt.Errorf("can't send update event -> %w", err)
//	}
//
//	return nil
//}
