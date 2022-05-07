package services

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/bus"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// TickersEdit сервис по редактированию перечня тикеров в портфеле.
//
// Редактирование осуществляется в рамках изолированной сессии. Начало нового редактирования сбрасывает предыдущую
// сессию. Результат редактирования сохраняется только после вызова соответствующего метода.
// Для тикеров в портфеле отслеживается появление новых дивидендов.
type TickersEdit struct {
	logger *lgr.Logger

	portfolio  repo.ReadWrite[domain.Position]
	securities repo.ReadWrite[domain.Security]

	lock sync.Mutex

	id   string
	port map[string]bool
	add  map[string]bool

	bus *bus.EventBus
}

// NewTickersEdit инициализирует сервис ручного ввода информации о тикерах в портфеле.
func NewTickersEdit(logger *lgr.Logger, db *mongo.Database, eventBus *bus.EventBus) *TickersEdit {
	return &TickersEdit{
		logger:     logger,
		portfolio:  repo.NewMongo[domain.Position](db),
		securities: repo.NewMongo[domain.Security](db),
		bus:        eventBus,
	}
}

// GetTickers создает новую сессию (удаляет старую) и возвращает перечень тикеров в текущем портфеле.
func (p *TickersEdit) GetTickers(ctx context.Context, sessionID string) ([]string, error) {
	port, err := p.portfolio.Get(ctx, domain.NewPositionsID())
	if err != nil {
		return nil, fmt.Errorf("can't load portfolio -> %w", err)
	}

	sec, err := p.securities.Get(ctx, domain.NewSecuritiesID())
	if err != nil {
		return nil, fmt.Errorf("can't load securities -> %w", err)
	}

	p.lock.Lock()
	defer p.lock.Unlock()

	p.id = sessionID

	var rez []string

	p.port = make(map[string]bool)
	for _, ticker := range port.Rows() {
		p.port[string(ticker)] = true

		rez = append(rez, string(ticker))
	}

	p.add = make(map[string]bool)
	for _, security := range sec.Rows() {
		if p.port[security.Ticker] {
			continue
		}

		p.add[security.Ticker] = true
	}

	return rez, nil
}

func (p *TickersEdit) sort(tickers map[string]bool) (sorted []string) {
	for ticker := range tickers {
		sorted = append(sorted, ticker)
	}

	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })

	return sorted
}

// SearchTickers возвращает перечень тикеров, начинающихся с указанных букв, которые могут быть добавлены в портфель.
func (p *TickersEdit) SearchTickers(sessionID, prefix string) ([]string, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.id != sessionID {
		return nil, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if prefix == "" {
		return nil, nil
	}

	prefix = strings.ToUpper(prefix)

	var found []string

	for ticker := range p.add {
		if strings.HasPrefix(ticker, prefix) {
			found = append(found, ticker)
		}
	}

	sort.Slice(found, func(i, j int) bool { return found[i] < found[j] })

	return found, nil
}

// AddTicker добавляет тикер в текущий портфель и возвращает его состав.
func (p *TickersEdit) AddTicker(sessionID, ticker string) ([]string, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.id != sessionID {
		return nil, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.add[ticker] {
		return nil, fmt.Errorf("incorrect ticker to add - %s", ticker)
	}

	delete(p.add, ticker)

	p.port[ticker] = true

	var port []string

	for ticker := range p.port {
		port = append(port, ticker)
	}

	sort.Slice(port, func(i, j int) bool { return port[i] < port[j] })

	return port, nil
}

// RemoveTicker удаляет тикер из портфеля и возвращает его состав.
func (p *TickersEdit) RemoveTicker(sessionID, ticker string) ([]string, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.id != sessionID {
		return nil, fmt.Errorf("wrong session id - %s", sessionID)
	}

	if !p.port[ticker] {
		return nil, fmt.Errorf("incorrect ticker to remove - %s", ticker)
	}

	delete(p.port, ticker)

	p.add[ticker] = true

	var port []string

	for ticker := range p.port {
		port = append(port, ticker)
	}

	sort.Slice(port, func(i, j int) bool { return port[i] < port[j] })

	return port, nil
}

// Save сохраняет результаты редактирования и возвращает количество тикеров в портфеле.
func (p *TickersEdit) Save(ctx context.Context, sessionID string) (int, error) {
	p.lock.Lock()
	defer p.lock.Unlock()

	if p.id != sessionID {
		return 0, fmt.Errorf("wrong session id - %s", sessionID)
	}

	var rows []domain.Position

	for ticker := range p.port {
		rows = append(rows, domain.Position(ticker))
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i] < rows[j] })

	err := p.portfolio.Replace(ctx, domain.NewTable(domain.NewPositionsID(), time.Now(), rows))
	if err != nil {
		return 0, fmt.Errorf("can't save portfolio -> %w", err)
	}

	err = p.bus.Send(domain.NewUpdateCompleted(domain.NewPositionsID()))
	if err != nil {
		return len(rows), fmt.Errorf("can't send update event -> %w", err)
	}

	return len(rows), nil
}
