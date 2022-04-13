// Package backup содержит правило, сохраняющее в ручную введенные данные.
package backup

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_group  = "backup"
	_folder = "dump"
)

// CollectionCmd - команда для сохранения коллекции данных.
type CollectionCmd func(ctx context.Context, collection string) error

// CreateCMD создает команду для сохранения коллекции данных.
func CreateCMD(uri, db string) CollectionCmd {
	return func(ctx context.Context, collection string) error {
		err := client.MongoDBBackUpCmd(ctx, _folder, uri, db, collection).Run()
		if err != nil {
			return fmt.Errorf(
				"can't back up data from MongoDB -> %w",
				err,
			)
		}

		return nil
	}
}

// Rule - правило, сохраняющее в ручную введенные данные после их обновления.
type Rule struct {
	logger  *lgr.Logger
	timeout time.Duration
	cmd     CollectionCmd
}

// New создает правило, сохраняющее в ручную введенные данные после их обновления.
func New(logger *lgr.Logger, cmd CollectionCmd, timeout time.Duration) *Rule {
	return &Rule{logger: logger, cmd: cmd, timeout: timeout}
}

// Activate возвращает исходящий канал с событиями об ошибке backup.
func (r *Rule) Activate(inbox <-chan domain.Event) <-chan domain.Event {
	out := make(chan domain.Event)

	go func() {
		r.logger.Infof("BackupRule: started")
		defer r.logger.Infof("BackupRule: stopped")

		defer close(out)

		for event := range inbox {
			if selected, ok := event.(domain.UpdateCompleted); ok {
				group := selected.Group()
				if group == domain.RawDivGroup || selected.ID() == domain.NewPositionsID() {
					r.backup(out, group)
				}
			}
		}
	}()

	return out
}

func (r *Rule) backup(out chan<- domain.Event, collection domain.Group) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	if err := r.cmd(ctx, string(collection)); err != nil {
		out <- domain.NewErrorOccurred(domain.NewID(_group, _group), err)

		return
	}

	r.logger.Infof("BackupRule: backup of %s collection completed", collection)
}
