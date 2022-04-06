// Package backup содержит правило, сохраняющее в ручную введенные данные.
package backup

import (
	"context"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"github.com/WLM1ke/poptimizer/data/internal/rules/div/raw"
	"github.com/WLM1ke/poptimizer/data/pkg/client"
	"github.com/WLM1ke/poptimizer/data/pkg/lgr"
)

const (
	_group  = "backup"
	_folder = "dump"
)

// Cmd - команда для сохранения данных.
type Cmd func(ctx context.Context) error

// CreateCMD создает команду для сохранения введенных вручную дивидендов.
func CreateCMD(uri, db string) func(ctx context.Context) error {
	return func(ctx context.Context) error {
		err := client.MongoDBBackUpCmd(ctx, _folder, uri, db, raw.Group).Run()
		if err != nil {
			return fmt.Errorf(
				"%w: can't back up data from MongoDB -> %s",
				domain.ErrRule,
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
	cmd     Cmd
}

// New правило, сохраняющее в ручную введенные данные после их обновления.
func New(logger *lgr.Logger, cmd Cmd, timeout time.Duration) *Rule {
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
				if selected.Group() == raw.Group {
					r.backup(out)
				}
			}
		}
	}()

	return out
}

func (r *Rule) backup(out chan<- domain.Event) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	if err := r.cmd(ctx); err != nil {
		out <- domain.NewErrorOccurred(domain.NewID(_group, _group), err)

		return
	}

	r.logger.Infof("BackupRule: backup of raw dividends completed")
}
