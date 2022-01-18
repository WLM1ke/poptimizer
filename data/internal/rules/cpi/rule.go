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

type CPI struct {
	Date  time.Time
	Close float64
}

func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	return template.NewRule[CPI](
		"CPIRule",
		logger,
		repo.NewMongo[CPI](db),
		selector{},
		gateway{client: client},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
