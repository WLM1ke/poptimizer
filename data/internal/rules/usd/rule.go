package usd

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

const _group = "usd"

var ID = domain.NewID(_group, _group)

func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	return template.NewRule[gomoex.Candle](
		"USDRule",
		logger,
		repo.NewMongo[gomoex.Candle](db),
		template.NewSelectOnTableUpdate(dates.ID, ID),
		gateway{iss: iss},
		validator,
		true,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
