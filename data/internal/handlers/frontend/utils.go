package frontend

import (
	"html/template"
	"net/http"

	"go.mongodb.org/mongo-driver/bson/primitive"
)

const (
	_tickers   = `Tickers`
	_dividends = `Dividends`
	_main      = `Main`
	_metrics   = `Metrics`
	_optimizer = `Optimizer`
	_reports   = `Reports`
)

func createSessionID() string {
	return primitive.NewObjectID().Hex()
}

func execTemplate(tmpl *template.Template, name string, page interface{}, w http.ResponseWriter) error {
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")

	err := tmpl.ExecuteTemplate(w, name, page)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}

	return err
}

type page struct {
	Menu      string
	SessionID string
	Sidebar   interface{}
	Main      interface{}
	Status    string
}
