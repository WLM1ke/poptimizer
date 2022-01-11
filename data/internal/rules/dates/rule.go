package dates

import (
	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"time"
)

// TODO все-таки версия должна быть привязана к диапазону торговых дат
func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	return template.NewRule[gomoex.Date](
		"DatesRule",
		logger,
		repo.NewMongo[gomoex.Date](db),
		selector{},
		gateway{iss: iss},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
