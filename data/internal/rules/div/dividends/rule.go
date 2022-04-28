package dividends

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правила обновления данных о дивидендах на основе вручную введенных дивидендов.
//
// Значения дивидендов пересчитываются в рубли для выплат в доллары и убирается информация о валюте.
func New(logger *lgr.Logger, database *mongo.Database, timeout time.Duration) domain.Rule {
	return template.NewRule[domain.Dividend](
		"DividendsRule",
		logger,
		repo.NewMongo[domain.Dividend](database),
		selector{securities: repo.NewMongo[domain.Security](database)},
		gateway{
			rawRepo: repo.NewMongo[domain.CurrencyDiv](database),
			usdRepo: repo.NewMongo[domain.USD](database),
		},
		validator,
		false,
		timeout,
	)
}
