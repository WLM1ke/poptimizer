package quotes

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	secRepo := repo.NewMongo[domain.Security](db)

	return template.NewRule[domain.Quote](
		"QuotesRule",
		logger,
		repo.NewMongo[domain.Quote](db),
		selector{secRepo},
		gateway{iss: iss, secRepo: secRepo},
		validator,
		true,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
