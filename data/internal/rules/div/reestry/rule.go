package reestry

import (
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило обновления дивидендов на https://закрытияреестров.рф/.
//
// Обновление происходит только после появления новых дивидендов в статусе для российских акций.
func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	statusRepo := repo.NewMongo[domain.DivStatus](db)

	return template.NewRule[domain.CurrencyDiv](
		"CheckCloseReestryDivRule",
		logger,
		repo.NewMongo[domain.CurrencyDiv](db),
		selector{statusRepo},
		gateway{statusRepo: statusRepo, client: client},
		validator,
		false,
		timeout,
	)
}
