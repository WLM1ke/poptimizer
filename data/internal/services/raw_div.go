package services

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"time"

	"github.com/jellydator/ttlcache/v3"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/div/raw"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_cacheTTL   = time.Minute * 10
	_timeFormat = "2006-01-02"
)

var errService = errors.New("service error")

// RawDivTableDTO представление информации о редактируемой таблице.
//
// Кроме данных таблицы хранит ID пользовательской сессии.
type RawDivTableDTO struct {
	SessionID string
	Ticker    string
	Rows      []domain.RawDiv
}

// NewRow шаблон для создания новой строки.
func (d RawDivTableDTO) NewRow() domain.RawDiv {
	if len(d.Rows) > 0 {
		return d.Rows[len(d.Rows)-1]
	}

	return domain.RawDiv{
		Date:     time.Now(),
		Value:    1,
		Currency: raw.RUR,
	}
}

// RowDTO - представление добавляемой строки.
type RowDTO domain.RawDiv

// StatusDTO - представление информации о сохранении измененной таблицы.
type StatusDTO struct {
	Name   string
	Status string
}

// RawDivUpdate - сервис, обрабатывающая запросы по изменению таблицы с дивидендами.
//
// Позволяет загрузить существующую таблицу с данными и создать соответсвующую пользовательскую сессию по
// редактированию. Добавлять новые строки, сбрасывать и сохранять изменения в рамках пользовательской сессии.
type RawDivUpdate struct {
	logger *lgr.Logger
	repo   repo.ReadWrite[domain.RawDiv]
	cache  *ttlcache.Cache[string, RawDivTableDTO]
	bus    *bus.EventBus
}

// NewRawDivUpdate инициализирует сервис.
func NewRawDivUpdate(logger *lgr.Logger, db *mongo.Database, bus *bus.EventBus) *RawDivUpdate {
	return &RawDivUpdate{
		logger: logger,
		repo:   repo.NewMongo[domain.RawDiv](db),
		cache:  ttlcache.New[string, RawDivTableDTO](ttlcache.WithTTL[string, RawDivTableDTO](_cacheTTL)),
		bus:    bus,
	}
}

// Run - запускает сервис.
func (r *RawDivUpdate) Run(ctx context.Context) error {
	go func() {
		r.cache.Start()
	}()

	<-ctx.Done()

	r.cache.Stop()

	return nil
}

// GetByTicker - возвращает сохраненные данные и создает пользовательскую сессию.
func (r *RawDivUpdate) GetByTicker(ctx context.Context, ticker string) (dto RawDivTableDTO, err error) {
	sessionID := primitive.NewObjectID().Hex()

	table, err := r.repo.Get(ctx, domain.NewID(raw.Group, ticker))
	if err != nil {
		return dto, fmt.Errorf(
			"%w: can't load data from repo -> %s",
			errService,
			err,
		)
	}

	dto = RawDivTableDTO{
		SessionID: sessionID,
		Ticker:    ticker,
		Rows:      table.Rows(),
	}

	r.cache.Set(sessionID, dto, ttlcache.DefaultTTL)

	return dto, nil
}

// AddRow добавляет новые строки в таблицу в рамках пользовательской сессии.
func (r *RawDivUpdate) AddRow(sessionID, date, value, currency string) (row RowDTO, err error) {
	item := r.cache.Get(sessionID)
	if item == nil {
		return row, fmt.Errorf(
			"%w: wrong id - %s",
			errService,
			sessionID,
		)
	}

	tableDTO := item.Value()

	row, err = parseRow(date, value, currency)
	if err != nil {
		return row, err
	}

	tableDTO.Rows = append(tableDTO.Rows, domain.RawDiv(row))
	r.cache.Set(sessionID, tableDTO, ttlcache.DefaultTTL)

	return row, nil
}

func parseRow(date string, value string, currency string) (row RowDTO, err error) {
	row.Date, err = time.Parse(_timeFormat, date)
	if err != nil {
		return row, fmt.Errorf(
			"%w: can't parse -> %s",
			errService,
			err,
		)
	}

	row.Value, err = strconv.ParseFloat(value, 64)
	if err != nil {
		return row, fmt.Errorf(
			"%w: can't parse -> %s",
			errService,
			err,
		)
	}

	row.Currency = currency
	if currency != raw.USD && currency != raw.RUR {
		return row, fmt.Errorf(
			"%w: incorrect currency - %s",
			errService,
			currency,
		)
	}

	return row, nil
}

// Reload сбрасывает результаты редактирования в рамках пользовательской сессии и возвращает не измененную таблицу.
func (r *RawDivUpdate) Reload(ctx context.Context, sessionID string) (dto RawDivTableDTO, err error) {
	item := r.cache.Get(sessionID)
	if item == nil {
		return dto, fmt.Errorf(
			"%w: wrong id - %s",
			errService,
			sessionID,
		)
	}

	ticker := item.Value().Ticker

	table, err := r.repo.Get(ctx, domain.NewID(raw.Group, ticker))
	if err != nil {
		return dto, fmt.Errorf(
			"%w: can't load data from repo -> %s",
			errService,
			err,
		)
	}

	dto = RawDivTableDTO{
		SessionID: sessionID,
		Ticker:    ticker,
		Rows:      table.Rows(),
	}
	r.cache.Set(sessionID, dto, ttlcache.DefaultTTL)

	return dto, nil
}

// Save сохраняет результаты редактирования и информирует об успешности отдельных этапов этого процесса.
func (r *RawDivUpdate) Save(ctx context.Context, sessionID string) (status []StatusDTO) {
	defer r.cache.Delete(sessionID)

	item := r.cache.Get(sessionID)
	if item == nil {
		return append(status, StatusDTO{"Loaded from cache", "wrong tableID"})
	}

	status = append(status, StatusDTO{"Loaded from cache", "OK"})

	dto := item.Value()

	tableID := domain.NewID(raw.Group, dto.Ticker)

	rows := dto.Rows
	sort.Slice(rows, func(i, j int) bool { return rows[i].Date.Before(rows[j].Date) })

	date := domain.LastTradingDate()

	err := r.repo.Replace(ctx, domain.NewTable(tableID, date, rows))
	if err != nil {
		return append(status, StatusDTO{"Saved to repo", err.Error()})
	}

	status = append(status, StatusDTO{"Saved to repo", "OK"})

	err = r.bus.Send(domain.NewUpdateCompleted(tableID))
	if err != nil {
		return append(status, StatusDTO{"Sent update event", err.Error()})
	}

	return append(status, StatusDTO{"Sent update event", "OK"})
}
