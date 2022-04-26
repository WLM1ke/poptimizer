package raw

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило проверки, что во вручную введенных дивидендах есть все новые дивиденды из статуса.
func New(logger *lgr.Logger, database *mongo.Database, timeout time.Duration) domain.Rule {
	statusRepo := repo.NewMongo[domain.DivStatus](database)

	return template.NewRule[domain.CurrencyDiv](
		"CheckRawDivRule",
		logger,
		repo.NewMongo[domain.CurrencyDiv](database),
		selector{statusRepo},
		gateway{statusRepo: statusRepo},
		validator,
		false,
		timeout,
	)
}
