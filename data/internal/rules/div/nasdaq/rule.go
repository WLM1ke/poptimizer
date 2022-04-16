package nasdaq

import (
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило обновления дивидендов на NASDAQ.
//
// Обновление происходит только после появления новых дивидендов в статусе для иностранных акций.
func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	statusRepo := repo.NewMongo[domain.DivStatus](db)

	return template.NewRule[domain.CurrencyDiv](
		"CheckNASDAQDivRule",
		logger,
		repo.NewMongo[domain.CurrencyDiv](db),
		selector{statusRepo},
		gateway{statusRepo: statusRepo, client: client},
		validator,
		false,
		timeout,
	)
}
