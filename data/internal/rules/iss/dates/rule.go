package dates

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило загрузки информации о торговых датах.
func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) template.Rule[domain.Date] {
	return template.NewRule[domain.Date](
		"DatesRule",
		logger,
		repo.NewMongo[domain.Date](db),
		selector{},
		gateway{iss: iss},
		validator,
		false,
		timeout,
	)
}
