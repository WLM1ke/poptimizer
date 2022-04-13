package indexes

import (
	"context"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
)

type selector struct{}

func (s selector) Select(_ context.Context, event domain.Event) (ids []domain.ID, err error) {
	switch selected := event.(type) {
	case domain.UpdateCompleted:
		if selected.ID() == domain.NewDateID() {
			for _, index := range [4]string{`MCFTRR`, `MEOGTRR`, `IMOEX`, `RVI`} {
				ids = append(ids, domain.NewIndexID(index))
			}
		}
	}

	return ids, err
}
