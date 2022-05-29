package port

import (
	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"go.mongodb.org/mongo-driver/mongo"
)

// Subdomain является наименованием поддомена информации о портфеле.
const Subdomain = `port`

// SubscribeHandlers регистрирует все обработчики событий поддомена нформации о портфеле.
func SubscribeHandlers(bus domain.Bus, db *mongo.Client) {
	bus.Subscribe(NewSelectedHandler(domain.NewRepo[Selected](db)))
}
