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
	indexes := [4]string{`MCFTRR`, `MEOGTRR`, `IMOEX`, `RVI`}

	ids := make([]domain.ID, 0, len(indexes))

	for _, index := range indexes {
		ids = append(ids, domain.NewIndexID(index))
	}

	return ids, nil
}
