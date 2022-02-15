package dates

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/end"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

const _group = "dates"

var ID = domain.NewID(_group, _group)

func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	return template.NewRule[gomoex.Date](
		"DatesRule",
		logger,
		repo.NewMongo[gomoex.Date](db),
		template.NewSelectOnTableUpdate(end.ID, ID),
		gateway{iss: iss},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
