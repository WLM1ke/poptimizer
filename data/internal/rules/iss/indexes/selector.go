package indexes

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) ([]domain.ID, error) {
	if selected, ok := event.(domain.UpdateCompleted); ok {
		if selected.ID() == domain.NewTradingDateID() {
			return s.ids()
		}
	}

	return nil, nil
}

func (s selector) ids() ([]domain.ID, error) {
	var ids []domain.ID

	for _, index := range [4]string{`MCFTRR`, `MEOGTRR`, `IMOEX`, `RVI`} {
		ids = append(ids, domain.NewIndexID(index))
	}

	return ids, nil
}
