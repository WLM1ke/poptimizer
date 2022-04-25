package indexes

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило загрузки основных индексов.
func New(
	logger *lgr.Logger,
	db *mongo.Database,
	iss *gomoex.ISSClient,
	timeout time.Duration,
) template.Rule[domain.Index] {
	return template.NewRule[domain.Index](
		"IndexesRule",
		logger,
		repo.NewMongo[domain.Index](db),
		selector{},
		gateway{iss: iss},
		validator,
		true,
		timeout,
	)
}
