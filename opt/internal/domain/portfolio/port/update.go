package port

import (
	"context"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/quote"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

// Repo для операций с портфелями счетами.
type Repo interface {
	domain.ReadRepo[Portfolio]
	domain.ReadGroupRepo[Portfolio]
	domain.WriteRepo[Portfolio]
}

// Service отвечающий за обновление счетов и суммарного портфеля с учетом новых рыночных данных.
type Service struct {
	logger lgr.Logger
	port   Repo
	sec    domain.ReadRepo[securities.Table]
	quotes domain.ReadRepo[quote.Table]
}

// NewService создает сервис для актуализации данных счетов и портфелей.
func NewService(
	logger lgr.Logger,
	port Repo,
	sec domain.ReadRepo[securities.Table],
	quotes domain.ReadRepo[quote.Table],
) *Service {
	return &Service{
		logger: logger,
		port:   port,
		sec:    sec,
		quotes: quotes,
	}
}

// Update актуализирует рыночные данные счетов и портфелей.
func (s Service) Update(ctx context.Context) {
	defer s.logger.Infof("update is finished")

	aggs, err := s.loadAcc(ctx)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	aggs, err = s.updateSec(ctx, aggs)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	port, err := s.loadPortfolio(ctx, aggs)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	cache, err := s.prepareCache(ctx, port)
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	for _, agg := range s.updateMarketData(append(aggs, port), cache) {
		err := s.port.Save(ctx, agg)
		if err != nil {
			s.logger.Warnf("%s", err)
		}
	}
}

func (s Service) loadAcc(ctx context.Context) ([]domain.Aggregate[Portfolio], error) {
	accounts, err := s.port.GetGroup(ctx, portfolio.Subdomain, _AccountsGroup)
	if err != nil {
		return nil, err
	}

	if len(accounts) > 0 {
		return accounts, nil
	}

	agg, err := s.port.Get(ctx, AccountID(_NewAccount))
	if err != nil {
		return nil, err
	}

	return append(accounts, agg), nil
}

func (s Service) updateSec(
	ctx context.Context,
	aggs []domain.Aggregate[Portfolio],
) ([]domain.Aggregate[Portfolio], error) {
	agg, err := s.sec.Get(ctx, securities.ID())
	if err != nil {
		return nil, err
	}

	date := agg.Timestamp()
	sec := agg.Entity()

	for nAgg := range aggs {
		account := aggs[nAgg].Entity()
		s.logErrs(account.updateSec(sec))
		aggs[nAgg].Update(account, date)
	}

	return aggs, nil
}

func (s Service) logErrs(errs []error) {
	for _, err := range errs {
		s.logger.Warnf("%s", err)
	}
}

func (s Service) loadPortfolio(
	ctx context.Context,
	aggs []domain.Aggregate[Portfolio],
) (domain.Aggregate[Portfolio], error) {
	port, err := s.port.Get(ctx, PortfolioDateID(aggs[0].Timestamp()))
	if err != nil {
		return nil, err
	}

	entity := aggs[0].Entity()

	for _, agg := range aggs {
		entity = entity.sum(agg.Entity())
	}

	port.Update(entity, aggs[0].Timestamp())

	return port, nil
}

func (s Service) prepareCache(
	ctx context.Context,
	port domain.Aggregate[Portfolio],
) (map[string]markerData, error) {
	positions := port.Entity().Positions
	date := port.Timestamp()

	cache := make(map[string]markerData, len(positions))

	for _, pos := range positions {
		agg, err := s.quotes.Get(ctx, quote.ID(pos.Ticker))
		if err != nil {
			return nil, err
		}

		cache[pos.Ticker] = calcMarkerData(date, agg.Entity())
	}

	return cache, nil
}

func (s *Service) updateMarketData(
	aggs []domain.Aggregate[Portfolio],
	cache map[string]markerData,
) []domain.Aggregate[Portfolio] {
	for nAgg := range aggs {
		account := aggs[nAgg].Entity()
		account.updateMarketData(cache)
		aggs[nAgg].UpdateSameDate(account)
	}

	return aggs
}
