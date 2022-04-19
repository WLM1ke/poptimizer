package securities

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило загрузки данных о торгующихся ценных бумагах.
func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) domain.Rule {
	return template.NewRule[domain.Security](
		"SecuritiesRule",
		logger,
		repo.NewMongo[domain.Security](db),
		selector{},
		gateway{iss: iss},
		validator,
		false,
		timeout,
	)
}
