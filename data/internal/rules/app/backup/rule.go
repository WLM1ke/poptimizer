// Package backup содержит правило, сохраняющее в ручную введенные данные.
package backup

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

const (
	_group  = "backup"
	_folder = "dump"
)

// Rule - правило, сохраняющее в ручную введенные данные после их обновления.
type Rule struct {
	logger  *lgr.Logger
	timeout time.Duration

	uri      string
	database *mongo.Database
}

// New создает правило, сохраняющее в ручную введенные данные после их обновления.
func New(
	logger *lgr.Logger,
	uri string,
	database *mongo.Database,
	timeout time.Duration,
) *Rule {
	return &Rule{logger: logger, uri: uri, database: database, timeout: timeout}
}

// Activate возвращает исходящий канал с событиями об ошибке runBackup.
func (r *Rule) Activate(inbox <-chan domain.Event) <-chan domain.Event {
	out := make(chan domain.Event)

	go func() {
		r.logger.Infof("BackupRule: started")
		defer r.logger.Infof("BackupRule: stopped")

		defer close(out)

		r.initCollections(out)

		for event := range inbox {
			if selected, ok := event.(domain.UpdateCompleted); ok {
				group := selected.Group()
				if group == domain.RawDivGroup || selected.ID() == domain.NewPositionsID() {
					r.runBackup(out, group)
				}
			}
		}
	}()

	return out
}

func (r *Rule) runBackup(out chan<- domain.Event, collection domain.Group) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	err := client.MongoDBBackup(ctx, _folder, r.uri, r.database.Name(), string(collection))
	if err != nil {
		out <- domain.NewErrorOccurred(domain.NewID(_group, _group), err)

		return
	}

	r.logger.Infof("BackupRule: backup of %s collection completed", collection)
}

func (r *Rule) initCollections(out chan<- domain.Event) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	for _, collection := range []string{string(domain.NewPositionsID().Group()), domain.RawDivGroup} {
		count, err := r.database.Collection(collection).CountDocuments(ctx, bson.D{})
		if err != nil {
			err = fmt.Errorf("can't count documents in %s -> %w", collection, err)
			out <- domain.NewErrorOccurred(domain.NewID(_group, _group), err)

			continue
		}

		if count > 0 {
			continue
		}

		err = client.MongoDBRestore(ctx, _folder, r.uri, r.database.Name(), collection)
		if err != nil {
			out <- domain.NewErrorOccurred(domain.NewID(_group, _group), err)

			continue
		}

		r.logger.Infof("BackupRule: default %s collection created", collection)
	}
}
