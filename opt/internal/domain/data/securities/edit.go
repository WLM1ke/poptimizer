package securities

import (
	"context"
	"time"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
)

const _backupTimeout = 30 * time.Second

// DTO с перечнем существующих тикеров.
type DTO []struct {
	Ticker   string `json:"ticker"`
	Selected bool   `json:"selected"`
}

// EditService позволяет редактировать перечень выбранных тикеров с помощью внешнего API.
type EditService struct {
	logger lgr.Logger
	repo   domain.ReadWriteRepo[Table]
	backup domain.Backup
}

// NewEditService создает сервис редактирования выбранных тикеров.
func NewEditService(
	logger lgr.Logger,
	repo domain.ReadWriteRepo[Table],
	backup domain.Backup,
) *EditService {
	return &EditService{logger: logger, repo: repo, backup: backup}
}

// Get предоставляет информацию о выбранных тикерах.
func (s EditService) Get(ctx context.Context) (DTO, domain.ServiceError) {
	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	table := agg.Entity()

	dto := make(DTO, len(table))

	for n, sec := range table {
		dto[n].Ticker = sec.Ticker
		dto[n].Selected = sec.Selected
	}

	return dto, nil
}

// Save сохраняет информацию о выбранных тикерах.
func (s EditService) Save(ctx context.Context, dto DTO) domain.ServiceError {
	agg, err := s.repo.Get(ctx, ID())
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	table := agg.Entity()

	if len(table) != len(dto) {
		return domain.NewBadServiceRequestErr("wrong tickers count %d vs %d", len(dto), len(table))
	}

	for n, row := range dto {
		if row.Ticker != table[n].Ticker {
			return domain.NewBadServiceRequestErr("wrong ticker %s vs %s", row.Ticker, table[n].Ticker)
		}

		table[n].Selected = row.Selected
	}

	if err := s.repo.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), _backupTimeout)
		defer cancel()

		if err := s.backup.Backup(ctx, data.Subdomain, _group); err != nil {
			s.logger.Warnf("%s", err)

			return
		}

		s.logger.Infof("backup of selected securities completed")
	}()

	return nil
}
