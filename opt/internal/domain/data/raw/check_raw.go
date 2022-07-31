package raw

import (
	"context"

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

// Check проверяет актуальность введенных пользователем дивидендов и возвращает перечень пропущенных.
func (s CheckRawService) Check(ctx context.Context, table StatusTable) (missed StatusTable) {
	defer s.logger.Infof("check is finished")

	for _, status := range table {
		if s.isMissed(ctx, status) {
			missed = append(missed, status)
		}
	}

	return missed
}

func (s CheckRawService) isMissed(ctx context.Context, status Status) bool {
	agg, err := s.repo.Get(ctx, ID(status.Ticker))
	if err != nil {
		s.logger.Warnf("%s", err)

		return false
	}

	if !agg.Entity().ExistsDate(status.Date) {
		s.logger.Warnf("missed %s dividend at %s", status.Ticker, status.Date.Format(_eventDateFormat))

		return true
	}

	return false
}
