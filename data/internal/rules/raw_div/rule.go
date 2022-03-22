package raw_div

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

func New(logger *lgr.Logger, db *mongo.Database, timeout time.Duration) domain.Rule {
	statusRepo := repo.NewMongo[domain.DivStatus](db)

	return template.NewRule[domain.RawDiv](
		"RawDivRule",
		logger,
		repo.NewMongo[domain.RawDiv](db),
		selector{statusRepo},
		gateway{statusRepo: statusRepo},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
