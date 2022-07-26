package raw

import (
	"context"
	"sync"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _eventDateFormat = `2006-01-02`

// CheckRawService проверяет актуальность введенных пользователем дивидендов.
type CheckRawService struct {
	logger lgr.Logger
	repo   domain.ReadRepo[Table]
}

// NewCheckRawService создает службу проверки актуальности введенных пользователем дивидендов.
func NewCheckRawService(
	logger lgr.Logger,
	repo domain.ReadRepo[Table],
) *CheckRawService {
	return &CheckRawService{
		logger: logger,
		repo:   repo,
	}
}

// Check проверяет актуальность введенных пользователем дивидендов.
func (s CheckRawService) Check(ctx context.Context, table StatusTable) {
	defer s.logger.Infof("check is finished")

	var waitGroup sync.WaitGroup
	defer waitGroup.Wait()

	for _, status := range table {
		waitGroup.Add(1)

		status := status

		go func() {
			defer waitGroup.Done()

			s.checkOne(ctx, status)
		}()
	}
}

func (s CheckRawService) checkOne(ctx context.Context, status Status) {
	agg, err := s.repo.Get(ctx, ID(status.Ticker))
	if err != nil {
		s.logger.Warnf("%s", err)

		return
	}

	if !agg.Entity().ExistsDate(status.Date) {
		s.logger.Warnf("missed %s dividend at %s", status.Ticker, status.Date.Format(_eventDateFormat))
	}
}
