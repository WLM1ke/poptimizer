package securities

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

// Service осуществляющий за обновление информации о торгуемых бумагах.
type Service struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	iss    *gomoex.ISSClient
}

// NewService создает сервис, отвечающий за обновление информации о торгуемых бумагах.
func NewService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	iss *gomoex.ISSClient,
) *Service {
	return &Service{
		logger: logger,
		repo:   repo,
		iss:    iss,
	}
}

// Update осуществляет загрузку данных о торгуемых бумагах.
//
// Объединяются данные по акциям, иностранным акциям и ETF.
func (s Service) Update(ctx context.Context, date time.Time) Table {
	defer s.logger.Infof("update is finished")

	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	raw, err := s.download(ctx)
	if err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	agg.Update(agg.Entity().update(raw), date)

	if err := s.repo.Save(ctx, agg); err != nil {
		s.logger.Warnf("%s", err)

		return nil
	}

	return agg.Entity()
}

func (s Service) download(
	ctx context.Context,
) (rows []gomoex.Security, err error) {
	marketsBoards := []struct {
		market string
		board  string
	}{
		{gomoex.MarketShares, gomoex.BoardTQBR},
		{gomoex.MarketShares, gomoex.BoardTQTF},
		{gomoex.MarketForeignShares, gomoex.BoardFQBR},
	}

	for _, marketBoard := range marketsBoards {
		candles, err := s.iss.BoardSecurities(ctx, gomoex.EngineStock, marketBoard.market, marketBoard.board)
		if err != nil {
			return nil, fmt.Errorf(
				"can't download securities data for market %s board %s-> %w",
				marketBoard.market,
				marketBoard.board,
				err,
			)
		}

		rows = append(rows, candles...)
	}

	sort.Slice(rows, func(i, j int) bool { return rows[i].Ticker < rows[j].Ticker })

	return rows, nil
}
