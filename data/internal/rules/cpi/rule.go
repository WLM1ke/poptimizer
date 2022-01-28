package cpi

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"net/http"
	"time"
)

const _group = "cpi"

var ID = domain.ID{Group: _group, Name: _group}

type CPI struct {
	Date  time.Time
	Close float64
}

func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	return template.NewRule[CPI](
		"CPIRule",
		logger,
		repo.NewMongo[CPI](db),
		template.NewSelectOnTableUpdate(dates.ID, ID),
		gateway{client: client},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
