package services

import (
	"context"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/iss/securities"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

const _group = `port`

// TickersDTO содержит перечень тикеров в рамках сессии по редактированию портфеля.
type TickersDTO struct {
	SessionID string
	tickers   map[domain.Ticker]bool
}

// NewTickersDTO создает новый перечень тикеров, привязанный к сессии.
func NewTickersDTO(sessionID string, tickers []domain.Ticker) TickersDTO {
	tickersMap := make(map[domain.Ticker]bool, len(tickers))
	for _, ticker := range tickers {
		tickersMap[ticker] = true
	}

	return TickersDTO{SessionID: sessionID, tickers: tickersMap}
}

// Tickers возвращает отсортированный перечень тикеров.
func (t TickersDTO) Tickers() []domain.Ticker {
	tickers := make([]domain.Ticker, 0, len(t.tickers))
	for ticker := range t.tickers {
		tickers = append(tickers, ticker)
	}

	sort.Slice(tickers, func(i, j int) bool { return tickers[i] < tickers[j] })

	return tickers
}

// PortfolioTickersEdit сервис по редактированию перечня тикеров в портфеле.
//
// Редактирование осуществляется в рамках изолированной сессии. Начало нового редактирования сбрасывает предыдущую
// сессию. Результат редактирования сохраняется только после вызова соответствующего метода.
// Для тикеров в портфеле отслеживается появление новых дивидендов.
type PortfolioTickersEdit struct {
	logger *lgr.Logger

	portfolio  repo.ReadWrite[domain.Ticker]
	securities repo.ReadWrite[domain.Security]

	lock sync.Mutex
	port TickersDTO
	add  TickersDTO

	bus *bus.EventBus
}

// NewPortfolioTickersEdit инициализирует сервис ручного ввода информации о тикерах в портфеле.
func NewPortfolioTickersEdit(logger *lgr.Logger, db *mongo.Database, bus *bus.EventBus) *PortfolioTickersEdit {
	return &PortfolioTickersEdit{
		logger:     logger,
		portfolio:  repo.NewMongo[domain.Ticker](db),
		securities: repo.NewMongo[domain.Security](db),
		bus:        bus,
	}
}

// GetTickers создает новую сессию (удаляет старую) и возвращает перечень тикеров в текущем портфеле.
func (p *PortfolioTickersEdit) GetTickers(ctx context.Context) (TickersDTO, error) {
	port, err := p.portfolio.Get(ctx, domain.NewID(_group, _group))
	if err != nil {
		return TickersDTO{}, fmt.Errorf("can't load portfolio -> %w", err)
	}

	sec, err := p.securities.Get(ctx, securities.ID)
	if err != nil {
		return TickersDTO{}, fmt.Errorf("can't load securities -> %w", err)
	}

	p.lock.Lock()
	defer p.lock.Unlock()

	id := primitive.NewObjectID().Hex()

	p.port = NewTickersDTO(id, port.Rows())
	p.add = NewTickersDTO(id, nil)

	for _, row := range sec.Rows() {
		ticker := domain.Ticker(row.Ticker)

		if !p.port.tickers[ticker] {
			p.add.tickers[ticker] = true
		}
	}

	return p.port, nil
}

// SearchTickers возвращает перечень тикеров, начинающихся с указанных букв, которые могут быть добавлены в портфель.
func (p *PortfolioTickersEdit) SearchTickers(sessionID, pattern string) (TickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	dto := NewTickersDTO(sessionID, nil)

	if p.port.SessionID != sessionID {
		return dto, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if pattern == "" {
		return dto, nil
	}

	re, err := regexp.Compile(fmt.Sprintf("^%s", strings.ToUpper(pattern)))
	if err != nil {
		return dto, fmt.Errorf("wrong pattern - %s", pattern)
	}

	for ticker := range p.add.tickers {
		if re.MatchString(string(ticker)) {
			dto.tickers[ticker] = true
		}
	}

	return dto, nil
}

// AddTicker добавляет тикер в текущий портфель и возвращает его состав.
func (p *PortfolioTickersEdit) AddTicker(sessionID, ticker string) (TickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.port.SessionID != sessionID {
		return TickersDTO{}, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.add.tickers[domain.Ticker(ticker)] {
		return TickersDTO{}, fmt.Errorf("incorrect ticker to add - %s", ticker)
	}

	delete(p.add.tickers, domain.Ticker(ticker))

	p.port.tickers[domain.Ticker(ticker)] = true

	return p.port, nil
}

// RemoveTicker удаляет тикер из портфеля и возвращает его состав.
func (p *PortfolioTickersEdit) RemoveTicker(sessionID, ticker string) (TickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.port.SessionID != sessionID {
		return TickersDTO{}, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.port.tickers[domain.Ticker(ticker)] {
		return TickersDTO{}, fmt.Errorf("incorrect ticker to remove - %s", ticker)
	}

	delete(p.port.tickers, domain.Ticker(ticker))

	p.add.tickers[domain.Ticker(ticker)] = true

	return p.port, nil
}

// Save сохраняет результаты редактирования, обнуляет сессию и возвращает количество тикеров в портфеле.
func (p *PortfolioTickersEdit) Save(ctx context.Context, sessionID string) (int, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	defer func() { p.port.SessionID = "" }()

	if p.port.SessionID != sessionID {
		return 0, fmt.Errorf("wrong session id - %s", sessionID)
	}

	err := p.portfolio.Replace(ctx, domain.NewTable(domain.NewID(_group, _group), time.Now(), p.port.Tickers()))
	if err != nil {
		return 0, fmt.Errorf("can't save portfolio -> %w", err)
	}

	err = p.bus.Send(domain.NewUpdateCompleted(domain.NewID(_group, _group)))
	if err != nil {
		return 0, fmt.Errorf("can't send update event -> %w", err)
	}

	return len(p.port.tickers), nil
}
