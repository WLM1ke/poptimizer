package div

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

const _timeFormat = "2006-01-02"

// rawDivTableDTO представление информации о редактируемой таблице.
//
// Кроме данных таблицы хранит ID пользовательской сессии.
type rawDivTableDTO struct {
	SessionID string
	Ticker    string
	Rows      []domain.CurrencyDiv
	source    []domain.CurrencyDiv
}

func (d rawDivTableDTO) Missed() (missed []domain.CurrencyDiv) {
	index := make(map[domain.CurrencyDiv]bool)

	for _, row := range d.Rows {
		index[row] = true
	}

	for _, row := range d.source {
		if row.Date.After(domain.FirstDividendDate()) && !index[row] {
			missed = append(missed, row)
		}
	}

	return missed
}

// NewRow шаблон для создания новой строки.
func (d rawDivTableDTO) NewRow() domain.CurrencyDiv {
	if missed := d.Missed(); len(missed) > 0 {
		return missed[0]
	}

	if len(d.Rows) > 0 {
		return d.Rows[len(d.Rows)-1]
	}

	return domain.CurrencyDiv{
		Date:     time.Now(),
		Value:    1,
		Currency: domain.RURCurrency,
	}
}

// rawDivEdit - сервис, обрабатывающая запросы по изменению таблицы с дивидендами.
//
// Позволяет загрузить существующую таблицу с данными и создать соответсвующую пользовательскую сессию по
// редактированию. Добавлять новые строки, сбрасывать и сохранять изменения в рамках пользовательской сессии.
type rawDivEdit struct {
	logger *lgr.Logger
	repo   repo.ReadWrite[domain.CurrencyDiv]

	lock     sync.Mutex
	tableDTO rawDivTableDTO

	bus *bus.EventBus
}

// newRawDivEdit инициализирует сервис ручного ввода дивидендов.
func newRawDivEdit(logger *lgr.Logger, db *mongo.Database, bus *bus.EventBus) *rawDivEdit {
	return &rawDivEdit{
		logger: logger,
		repo:   repo.NewMongo[domain.CurrencyDiv](db),
		bus:    bus,
	}
}

// GetByTicker - возвращает сохраненные данные и создает пользовательскую сессию.
func (r *rawDivEdit) GetByTicker(ctx context.Context, ticker string) (rawDivTableDTO, error) {
	raw, err := r.repo.Get(ctx, domain.NewRawDivID(ticker))
	if err != nil {
		return rawDivTableDTO{}, fmt.Errorf(
			"can't load raw dividends from repo -> %w",
			err,
		)
	}

	id := domain.NewReestryDivID(ticker)
	if domain.IsForeignTicker(ticker) {
		id = domain.NewNASDAQDivID(ticker)
	}

	source, err := r.repo.Get(ctx, id)
	if err != nil {
		return rawDivTableDTO{}, fmt.Errorf(
			"can't load source dividends from repo -> %w",
			err,
		)
	}

	r.lock.Lock()
	defer r.lock.Unlock()

	r.tableDTO = rawDivTableDTO{
		SessionID: primitive.NewObjectID().Hex(),
		Ticker:    ticker,
		Rows:      raw.Rows(),
		source:    source.Rows(),
	}

	return r.tableDTO, nil
}

// AddRow добавляет новые строки в таблицу в рамках пользовательской сессии.
func (r *rawDivEdit) AddRow(sessionID, date, value, currency string) (rawDivTableDTO, error) {
	r.lock.Lock()
	defer r.lock.Unlock()

	if sessionID != r.tableDTO.SessionID {
		return r.tableDTO, fmt.Errorf(
			"wrong session id - %s",
			sessionID,
		)
	}

	row, err := parseRow(date, value, currency)
	if err != nil {
		return r.tableDTO, err
	}

	r.tableDTO.Rows = append(r.tableDTO.Rows, row)

	return r.tableDTO, nil
}

func parseRow(date string, value string, currency string) (row domain.CurrencyDiv, err error) {
	row.Date, err = time.Parse(_timeFormat, date)
	if err != nil {
		return row, fmt.Errorf(
			"can't parse -> %w",
			err,
		)
	}

	row.Value, err = strconv.ParseFloat(value, 64)
	if err != nil {
		return row, fmt.Errorf(
			"can't parse -> %w",
			err,
		)
	}

	row.Currency = currency
	if currency != domain.USDCurrency && currency != domain.RURCurrency {
		return row, fmt.Errorf(
			"incorrect currency - %s",
			currency,
		)
	}

	return row, nil
}

// Reload сбрасывает результаты редактирования в рамках пользовательской сессии и возвращает не измененную таблицу.
func (r *rawDivEdit) Reload(ctx context.Context, sessionID string) (dto rawDivTableDTO, err error) {
	r.lock.Lock()
	defer r.lock.Unlock()

	if sessionID != r.tableDTO.SessionID {
		return dto, fmt.Errorf(
			"wrong session id - %s",
			sessionID,
		)
	}

	table, err := r.repo.Get(ctx, domain.NewRawDivID(r.tableDTO.Ticker))
	if err != nil {
		return dto, fmt.Errorf(
			"can't load data from repo -> %w",
			err,
		)
	}

	r.tableDTO.Rows = table.Rows()

	return r.tableDTO, nil
}

// Save сохраняет результаты редактирования.
func (r *rawDivEdit) Save(ctx context.Context, sessionID string) error {
	r.lock.Lock()
	defer r.lock.Unlock()

	defer func() { r.tableDTO.SessionID = "" }()

	if sessionID != r.tableDTO.SessionID {
		return fmt.Errorf(
			"wrong session id - %s",
			sessionID,
		)
	}

	tableID := domain.NewRawDivID(r.tableDTO.Ticker)

	rows := r.tableDTO.Rows
	sort.Slice(rows, func(i, j int) bool { return rows[i].Date.Before(rows[j].Date) })

	err := r.repo.Replace(ctx, domain.NewTable(tableID, time.Now(), rows))
	if err != nil {
		return fmt.Errorf("can't save to repo -> %w", err)
	}

	err = r.bus.Send(domain.NewUpdateCompleted(tableID))
	if err != nil {
		return fmt.Errorf("can't send update event -> %w", err)
	}

	return nil
}
