package usd

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило загрузки котировок доллара.
func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) template.Rule[domain.USD] {
	return template.NewRule[domain.USD](
		"USDRule",
		logger,
		repo.NewMongo[domain.USD](db),
		selector{},
		gateway{iss: iss},
		validator,
		true,
		timeout,
	)
}
