package securities

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/internal/rules/usd"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

const _group = "securities"

var ID = domain.ID{Group: _group, Name: _group}

func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	return template.NewRule[gomoex.Security](
		"SecuritiesRule",
		logger,
		repo.NewMongo[gomoex.Security](db),
		template.NewSelectOnTableUpdate(usd.ID, ID),
		gateway{iss: iss},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
