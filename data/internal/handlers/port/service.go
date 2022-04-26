package port

import (
	"context"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

// tickersDTO содержит перечень тикеров в рамках сессии по редактированию портфеля.
type tickersDTO struct {
	SessionID string
	tickers   map[domain.Position]bool
}

// newTickersDTO создает новый перечень тикеров, привязанный к сессии.
func newTickersDTO(sessionID string, tickers []domain.Position) tickersDTO {
	tickersMap := make(map[domain.Position]bool, len(tickers))
	for _, ticker := range tickers {
		tickersMap[ticker] = true
	}

	return tickersDTO{SessionID: sessionID, tickers: tickersMap}
}

// Tickers возвращает отсортированный перечень тикеров.
func (t tickersDTO) Tickers() []domain.Position {
	tickers := make([]domain.Position, 0, len(t.tickers))
	for ticker := range t.tickers {
		tickers = append(tickers, ticker)
	}

	sort.Slice(tickers, func(i, j int) bool { return tickers[i] < tickers[j] })

	return tickers
}

// portfolioTickersEdit сервис по редактированию перечня тикеров в портфеле.
//
// Редактирование осуществляется в рамках изолированной сессии. Начало нового редактирования сбрасывает предыдущую
// сессию. Результат редактирования сохраняется только после вызова соответствующего метода.
// Для тикеров в портфеле отслеживается появление новых дивидендов.
type portfolioTickersEdit struct {
	logger *lgr.Logger

	portfolio  repo.ReadWrite[domain.Position]
	securities repo.ReadWrite[domain.Security]

	lock sync.Mutex
	port tickersDTO
	add  tickersDTO

	bus *bus.EventBus
}

// newPortfolioTickersEdit инициализирует сервис ручного ввода информации о тикерах в портфеле.
func newPortfolioTickersEdit(logger *lgr.Logger, db *mongo.Database, bus *bus.EventBus) *portfolioTickersEdit {
	return &portfolioTickersEdit{
		logger:     logger,
		portfolio:  repo.NewMongo[domain.Position](db),
		securities: repo.NewMongo[domain.Security](db),
		bus:        bus,
	}
}

// GetTickers создает новую сессию (удаляет старую) и возвращает перечень тикеров в текущем портфеле.
func (p *portfolioTickersEdit) GetTickers(ctx context.Context) (tickersDTO, error) {
	port, err := p.portfolio.Get(ctx, domain.NewPositionsID())
	if err != nil {
		return tickersDTO{}, fmt.Errorf("can't load portfolio -> %w", err)
	}

	sec, err := p.securities.Get(ctx, domain.NewSecuritiesID())
	if err != nil {
		return tickersDTO{}, fmt.Errorf("can't load securities -> %w", err)
	}

	p.lock.Lock()
	defer p.lock.Unlock()

	id := primitive.NewObjectID().Hex()

	p.port = newTickersDTO(id, port.Rows())
	p.add = newTickersDTO(id, nil)

	for _, row := range sec.Rows() {
		ticker := domain.Position(row.Ticker)

		if !p.port.tickers[ticker] {
			p.add.tickers[ticker] = true
		}
	}

	return p.port, nil
}

// SearchTickers возвращает перечень тикеров, начинающихся с указанных букв, которые могут быть добавлены в портфель.
func (p *portfolioTickersEdit) SearchTickers(sessionID, pattern string) (tickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	dto := newTickersDTO(sessionID, nil)

	if p.port.SessionID != sessionID {
		return dto, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if pattern == "" {
		return dto, nil
	}

	reTicker, err := regexp.Compile(fmt.Sprintf("^%s", strings.ToUpper(pattern)))
	if err != nil {
		return dto, fmt.Errorf("wrong pattern - %s", pattern)
	}

	for ticker := range p.add.tickers {
		if reTicker.MatchString(string(ticker)) {
			dto.tickers[ticker] = true
		}
	}

	return dto, nil
}

// AddTicker добавляет тикер в текущий портфель и возвращает его состав.
func (p *portfolioTickersEdit) AddTicker(sessionID, ticker string) (tickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.port.SessionID != sessionID {
		return tickersDTO{}, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.add.tickers[domain.Position(ticker)] {
		return tickersDTO{}, fmt.Errorf("incorrect ticker to add - %s", ticker)
	}

	delete(p.add.tickers, domain.Position(ticker))

	p.port.tickers[domain.Position(ticker)] = true

	return p.port, nil
}

// RemoveTicker удаляет тикер из портфеля и возвращает его состав.
func (p *portfolioTickersEdit) RemoveTicker(sessionID, ticker string) (tickersDTO, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.port.SessionID != sessionID {
		return tickersDTO{}, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.port.tickers[domain.Position(ticker)] {
		return tickersDTO{}, fmt.Errorf("incorrect ticker to remove - %s", ticker)
	}

	delete(p.port.tickers, domain.Position(ticker))

	p.add.tickers[domain.Position(ticker)] = true

	return p.port, nil
}

// Save сохраняет результаты редактирования, обнуляет сессию и возвращает количество тикеров в портфеле.
func (p *portfolioTickersEdit) Save(ctx context.Context, sessionID string) (int, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	defer func() { p.port.SessionID = "" }()

	if p.port.SessionID != sessionID {
		return 0, fmt.Errorf("wrong session id - %s", sessionID)
	}

	err := p.portfolio.Replace(ctx, domain.NewTable(domain.NewPositionsID(), time.Now(), p.port.Tickers()))
	if err != nil {
		return 0, fmt.Errorf("can't save portfolio -> %w", err)
	}

	err = p.bus.Send(domain.NewUpdateCompleted(domain.NewPositionsID()))
	if err != nil {
		return 0, fmt.Errorf("can't send update event -> %w", err)
	}

	return len(p.port.tickers), nil
}
