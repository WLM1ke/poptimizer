package data

import (
	"time"

	"github.com/WLM1ke/gomoex"
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"go.mongodb.org/mongo-driver/mongo"
)

// Subdomain является наименованием поддомена сбора данных.
const Subdomain = `data`

// SubscribeHandlers регистрирует все обработчики событий поддомена сбора данных.
func SubscribeHandlers(bus domain.Bus, db *mongo.Client, iss *gomoex.ISSClient) {
	bus.Subscribe(NewTradingDateHandler(bus, domain.NewRepo[time.Time](db), iss))
	bus.Subscribe(NewUSDHandler(bus, domain.NewRepo[Rows[USD]](db), iss))
	bus.Subscribe(NewSecuritiesHandler(bus, domain.NewRepo[Rows[Security]](db), iss))
}
