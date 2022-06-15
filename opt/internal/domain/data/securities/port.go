package securities

import (
	"context"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
)

type DTO []struct {
	Ticker   string `json:"ticker"`
	Selected bool   `json:"selected"`
}

// ViewPort предоставляет информацию о выбранных бумагах для внешних пользователей.
type ViewPort struct {
	repo domain.ReadWriteRepo[Table]
	pub  domain.Publisher
}

// NewViewPort создает порт для предоставления информации о выбранных бумагах.
func NewViewPort(
	repo domain.ReadWriteRepo[Table],
	pub domain.Publisher,
) *ViewPort {
	return &ViewPort{repo: repo, pub: pub}
}

func (c ViewPort) Get(ctx context.Context) (DTO, domain.ViewPortError) {
	agg, err := c.repo.Get(ctx, ID())
	if err != nil {
		return nil, domain.NewInternalErr(err)
	}

	dto := make(DTO, len(agg.Entity))

	for n, sec := range agg.Entity {
		dto[n].Ticker = sec.Ticker
		dto[n].Selected = sec.Selected
	}

	return dto, nil
}

func (c ViewPort) Save(ctx context.Context, dto DTO) domain.ViewPortError {
	agg, err := c.repo.Get(ctx, ID())
	if err != nil {
		return domain.NewInternalErr(err)
	}

	if len(agg.Entity) != len(dto) {
		return domain.NewBadDTOErr("wrong tickers count %d vs %d", len(dto), len(agg.Entity))
	}

	for n, row := range dto {
		if row.Ticker != agg.Entity[n].Ticker {
			return domain.NewBadDTOErr("wrong ticker %s vs %s", row.Ticker, agg.Entity[n].Ticker)
		}

		agg.Entity[n].Selected = row.Selected
	}

	if err := c.repo.Save(ctx, agg); err != nil {
		return domain.NewInternalErr(err)
	}

	c.pub.Publish(domain.Event{
		QualifiedID: ID(),
		Timestamp:   agg.Timestamp,
		Data:        agg.Entity,
	})

	return nil
}
