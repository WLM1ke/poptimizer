package securities

import (
	"context"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

// DTO представляет информацию, о том какие из существующих тикеров выбраны.
type DTO []struct {
	Ticker   string `json:"ticker"`
	Selected bool   `json:"selected"`
}

// Service предоставляет информацию о выбранных бумагах для внешних пользователей.
type Service struct {
	repo domain.ReadWriteRepo[Table]
	pub  domain.Publisher
}

// NewService создает порт для предоставления информации о выбранных бумагах.
func NewService(
	repo domain.ReadWriteRepo[Table],
	pub domain.Publisher,
) *Service {
	return &Service{repo: repo, pub: pub}
}

// Get предоставляет информацию о выбранных тикерах.
func (c Service) Get(ctx context.Context) (DTO, domain.ServiceError) {
	agg, err := c.repo.Get(ctx, GroupID())
	if err != nil {
		return nil, domain.NewServiceInternalErr(err)
	}

	dto := make(DTO, len(agg.Entity))

	for n, sec := range agg.Entity {
		dto[n].Ticker = sec.Ticker
		dto[n].Selected = sec.Selected
	}

	return dto, nil
}

// Save сохраняет информацию о выбранных тикерах.
func (c Service) Save(ctx context.Context, dto DTO) domain.ServiceError {
	agg, err := c.repo.Get(ctx, GroupID())
	if err != nil {
		return domain.NewServiceInternalErr(err)
	}

	if len(agg.Entity) != len(dto) {
		return domain.NewBadServiceRequestErr("wrong tickers count %d vs %d", len(dto), len(agg.Entity))
	}

	for n, row := range dto {
		if row.Ticker != agg.Entity[n].Ticker {
			return domain.NewBadServiceRequestErr("wrong ticker %s vs %s", row.Ticker, agg.Entity[n].Ticker)
		}

		agg.Entity[n].Selected = row.Selected
	}

	if err := c.repo.Save(ctx, agg); err != nil {
		return domain.NewServiceInternalErr(err)
	}

	c.pub.Publish(domain.Event{
		QualifiedID: GroupID(),
		Timestamp:   agg.Timestamp,
		Data:        agg.Entity,
	})

	return nil
}
