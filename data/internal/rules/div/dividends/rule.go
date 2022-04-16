package dividends

import (
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

func New(logger *lgr.Logger, db *mongo.Database, timeout time.Duration) domain.Rule {
	return template.NewRule[domain.Dividend](
		"DividendsRule",
		logger,
		repo.NewMongo[domain.Dividend](db),
		selector{},
		gateway{
			rawRepo: repo.NewMongo[domain.CurrencyDiv](db),
			usdRepo: repo.NewMongo[domain.USD](db),
		},
		validator,
		false,
		timeout,
	)
}
