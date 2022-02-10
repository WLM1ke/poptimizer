package status

import (
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/dates"
	"github.com/WLM1ke/poptimizer/data/internal/rules/securities"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
	"net/http"
	"time"
)

const _group = "status"

var ID = domain.ID{Group: _group, Name: _group}

type DivStatus struct {
	Ticker string
	Date   time.Time
}

// Возможные альтернативные источники:
// - https://smart-lab.ru/dividends/index/order_by_yield/desc/
// - https://закрытияреестров.рф
// - https://dividend.company
// Теоретически можно проверять коректность распознования тикеров, но в этом кажется нет необходимости
// Тесты для VEON-RX, AKRN и T-RM
func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) domain.Rule {
	return template.NewRule[DivStatus](
		"DivStatus",
		logger,
		repo.NewMongo[DivStatus](db),
		template.NewSelectOnTableUpdate(dates.ID, ID),
		gateway{client: client},
		validator,
		false,
		template.EventCtxFuncWithTimeout(timeout),
	)
}
