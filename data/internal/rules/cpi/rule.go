package cpi

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"net/http"
	"time"
)

func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	return template.NewRule[domain.CPI](
		"CPIRule",
		logger,
		repo.NewMongo[domain.CPI](db),
		selector{},
		gateway{client: client},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
