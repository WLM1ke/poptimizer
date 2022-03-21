package dividends

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

func New(logger *lgr.Logger, db *mongo.Database, timeout time.Duration) domain.Rule {
	return template.NewRule[Dividend](
		"DividendsRule",
		logger,
		repo.NewMongo[Dividend](db),
		selector{repo.NewMongo[gomoex.Security](db)},
		gateway{
			rawRepo: repo.NewMongo[RawDiv](db),
			usdRepo: repo.NewMongo[gomoex.Candle](db),
		},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
