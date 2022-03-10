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
	sg := &selectorWithGateway{
		iss:  iss,
		repo: repo.NewMongo[gomoex.Security](db),
	}

	return template.NewRule[gomoex.Candle](
		"QuotesRule",
		logger,
		repo.NewMongo[gomoex.Candle](db),
		sg,
		sg,
		validator,
		true,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
