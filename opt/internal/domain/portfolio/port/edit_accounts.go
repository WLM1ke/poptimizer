package port

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/portfolio"
)

// AccEditRepo необходимо для обновления брокерских счетов.
type AccEditRepo interface {
	domain.ReadWriteRepo[Portfolio]
	domain.ReadGroupRepo[Portfolio]
	domain.DeleteRepo
	domain.ListRepo
}

// AccEditService для редактирования брокерских счетов.
type AccEditService struct {
	repo AccEditRepo
}

// NewAccEditService создает сервис редактирования брокерских счетов.
func NewAccEditService(repo AccEditRepo) *AccEditService {
	return &AccEditService{repo: repo}
}

// AccountsDTO содержит перечень доступных счетов.
type AccountsDTO []string

// GetAccountNames возвращает перечень существующих счетов.
func (s AccEditService) GetAccountNames(ctx context.Context) (AccountsDTO, domain.ServiceError) {
	qids, err := s.repo.List(ctx, portfolio.Subdomain, _AccountsGroup)
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	if len(qids) <= 1 {
		return nil, nil
	}

	acc := make(AccountsDTO, 0, len(qids)-1)

	for _, qid := range qids {
		if qid != _NewAccount {
			acc = append(acc, qid)
		}
	}

	return acc, nil
}

// CreateAccount создает новый счет с выбранными бумагами.
func (s AccEditService) CreateAccount(ctx context.Context, name string) domain.ServiceError {
	if name == _NewAccount {
		return domain.NewBadServiceRequestErr("reserved name %s", name)
	}

	tmplAgg, err := s.repo.Get(ctx, AccountID(_NewAccount))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	agg, err := s.repo.Get(ctx, AccountID(name))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	if !agg.Timestamp().IsZero() {
		return domain.NewBadServiceRequestErr("can't create existing account %s", name)
	}

	agg.Update(tmplAgg.Entity(), tmplAgg.Timestamp())

	if err := s.repo.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}

// DeleteAccount удаляет счет.
func (s AccEditService) DeleteAccount(ctx context.Context, name string) domain.ServiceError {
	err := s.repo.Delete(ctx, AccountID(name))
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}

// AccountDTO информация об отдельном счете.
type AccountDTO Portfolio

// GetAccount выдает информацию о счет по указанному имени.
func (s AccEditService) GetAccount(ctx context.Context, name string) (AccountDTO, domain.ServiceError) {
	var dto AccountDTO

	agg, err := s.repo.Get(ctx, AccountID(name))
	if err != nil {
		return dto, domain.NewServiceInternalErr(err)
	}

	dto = AccountDTO(agg.Entity())

	if len(dto.Positions) == 0 {
		return dto, domain.NewServiceInternalErr(fmt.Errorf("wrong account name %s", name))
	}

	return dto, nil
}

// UpdateDTO содержит информацию об обновленных позициях.
type UpdateDTO []struct {
	Ticker string `json:"ticker"`
	Shares int    `json:"shares"`
}

// UpdateAccount меняет значение количества акций для заданного счета и тикера и обновляет информацию о портфеле.
//
// Для изменения количества денег необходимо указать тикер CASH.
func (s AccEditService) UpdateAccount(ctx context.Context, name string, dto UpdateDTO) domain.ServiceError {
	aggs, err := s.repo.GetGroup(ctx, portfolio.Subdomain, _AccountsGroup)
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	portQID := PortfolioDateID(aggs[0].Timestamp())

	port, err := s.repo.Get(ctx, portQID)
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	newPort := aggs[0].Entity()

	for count, agg := range aggs {
		if agg.QID().ID == name {
			acc := agg.Entity()

			for _, pos := range dto {
				if err := acc.SetAmount(pos.Ticker, pos.Shares); err != nil {
					return domain.NewBadServiceRequestErr("%s", err)
				}
			}

			agg.UpdateSameDate(acc)

			if err := s.repo.Save(ctx, agg); err != nil {
				return domain.NewServiceInternalErr(err)
			}
		}

		if count == 0 {
			continue
		}

		newPort = newPort.sum(agg.Entity())
	}

	port.UpdateSameDate(newPort)

	if err := s.repo.Save(ctx, port); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	return nil
}
