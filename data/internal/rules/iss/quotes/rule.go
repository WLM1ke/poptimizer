package quotes

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New создает правило загрузки котировок торгуемых ценных бумаг.
func New(logger *lgr.Logger, db *mongo.Database, iss *gomoex.ISSClient, timeout time.Duration) template.Rule[domain.Quote] {
	secRepo := repo.NewMongo[domain.Security](db)

	return template.NewRule[domain.Quote](
		"QuotesRule",
		logger,
		repo.NewMongo[domain.Quote](db),
		selector{secRepo},
		gateway{iss: iss, secRepo: secRepo},
		validator,
		true,
		timeout,
	)
}
