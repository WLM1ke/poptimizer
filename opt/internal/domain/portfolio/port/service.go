package port

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

// Service сервис для редактирования счетов.
type Service struct {
	repo domain.ReadGroupWriteDeleteRepo[Portfolio]
}

// NewService создает сервис редактирования брокерских счетов.
func NewService(repo domain.ReadGroupWriteDeleteRepo[Portfolio]) *Service {
	return &Service{repo: repo}
}

// AccountsDTO содержит перечень доступных сетов.
type AccountsDTO []string

// GetAccountNames возвращает перечень существующих счетов.
func (s Service) GetAccountNames(ctx context.Context) (AccountsDTO, domain.ServiceError) {
	aggs, err := s.repo.GetGroup(ctx, portfolio.Subdomain, _Group)
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	if len(aggs) <= 1 {
		return nil, nil
	}

	acc := make(AccountsDTO, 0, len(aggs)-1)

	for _, agg := range aggs {
		if agg.QID() != ID(_NewAccount) {
			acc = append(acc, agg.QID().ID)
		}
	}

	return acc, nil
}

// CreateAccount создает новый счет с выбранными бумагами.
func (s Service) CreateAccount(ctx context.Context, name string) domain.ServiceError {
	tmplAgg, err := s.repo.Get(ctx, ID(_NewAccount))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	agg, err := s.repo.Get(ctx, ID(name))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	agg.Timestamp = tmplAgg.Timestamp
	agg.Entity = tmplAgg.Entity

	if err := s.repo.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}

// DeleteAccount удаляет счет.
func (s Service) DeleteAccount(ctx context.Context, name string) domain.ServiceError {
	err := s.repo.Delete(ctx, ID(name))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}

// PositionDTO информация об отдельной позиции.
type PositionDTO struct {
	Ticker string  `json:"ticker"`
	Shares int     `json:"shares"`
	Lot    int     `json:"lot"`
	Price  float64 `json:"price"`
}

// AccountDTO информация об отдельном счете.
type AccountDTO struct {
	Positions []PositionDTO `json:"positions"`
	Cash      int           `json:"cash"`
}

// GetAccount выдает информацию о счет по указанному имени.
func (s Service) GetAccount(ctx context.Context, name string) (AccountDTO, domain.ServiceError) {
	var dto AccountDTO

	agg, err := s.repo.Get(ctx, ID(name))
	if err != nil {
		return dto, domain.NewServiceInternalErr(err)
	}

	if len(agg.Entity.Positions) == 0 {
		return dto, domain.NewServiceInternalErr(fmt.Errorf("wrong account name %s", name))
	}

	dto.Cash = agg.Entity.Cash

	for _, pos := range agg.Entity.Positions {
		dto.Positions = append(dto.Positions, PositionDTO{
			Ticker: pos.Ticker,
			Shares: pos.Shares,
			Lot:    pos.Lot,
			Price:  pos.Price,
		})
	}

	return dto, nil
}

// UpdateDTO содержит информацию об обновленных позициях.
type UpdateDTO []struct {
	Ticker string `json:"ticker"`
	Shares int    `json:"shares"`
}

// UpdateAccount меняет значение количества акций для заданного счета и тикера.
//
// Для изменения количества денег необходимо указать тикер CASH.
func (s Service) UpdateAccount(ctx context.Context, name string, dto UpdateDTO) domain.ServiceError {
	agg, err := s.repo.Get(ctx, ID(name))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	for _, pos := range dto {
		if err := agg.Entity.SetAmount(pos.Ticker, pos.Shares); err != nil {
			return domain.NewBadServiceRequestErr("%s", err)
		}
	}

	if err := s.repo.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}
