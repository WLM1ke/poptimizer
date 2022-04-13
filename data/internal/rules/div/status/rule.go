package status

import (
	"net/http"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/repo"
	"github.com/WLM1ke/poptimizer/data/internal/rules/template"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

// New - создает новое правило загрузки данных о новых дивидендах.
// Возможные альтернативные источники:
// - https://smart-lab.ru/dividends/index/order_by_yield/desc/
// - https://закрытияреестров.рф
// - https://dividend.company
// Теоретически можно проверять корректность распознавания тикеров, но в этом кажется нет необходимости
// Тесты для VEON-RX, AKRN и T-RM.
func New(logger *lgr.Logger, db *mongo.Database, client *http.Client, timeout time.Duration) template.Rule[domain.DivStatus] {
	return template.NewRule[domain.DivStatus](
		"DivStatusRule",
		logger,
		repo.NewMongo[domain.DivStatus](db),
		selector{},
		gateway{client: client, repo: repo.NewMongo[domain.Position](db)},
		validator,
		false,
		timeout,
	)
}
