package port

import (
	"context"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

// ViewPortfolioRepo необходимое для просмотра данных о структуре портфеля.
type ViewPortfolioRepo interface {
	domain.ReadRepo[Portfolio]
	domain.ListRepo
}

// ViewPortfolioService для просмотра портфеля, в том числе исторических значений.
type ViewPortfolioService struct {
	repo ViewPortfolioRepo
}

// NewViewPortfolioService создает сервис для просмотра информации о портфеле.
func NewViewPortfolioService(repo ViewPortfolioRepo) *ViewPortfolioService {
	return &ViewPortfolioService{repo: repo}
}

// GetDates выдает перечень дат, для которых есть информация о портфеле.
func (s ViewPortfolioService) GetDates(ctx context.Context) (AccountsDTO, domain.ServiceError) {
	qids, err := s.repo.List(ctx, portfolio.Subdomain, _PortfolioGroup)
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	return qids, nil
}

// Get выдает информацию о портфеле для заданной даты.
func (s ViewPortfolioService) Get(ctx context.Context, date string) (AccountDTO, domain.ServiceError) {
	agg, err := s.repo.Get(ctx, PortfolioID(date))
	if err != nil {
		return AccountDTO{}, domain.NewServiceInternalErr(err)
	}

	if len(agg.Entity().Positions) == 0 {
		return AccountDTO{}, domain.NewBadServiceRequestErr("wrong portfolio date %s", date)
	}

	return AccountDTO(agg.Entity()), nil
}
