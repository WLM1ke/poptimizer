package app

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/port/selected"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/WLM1ke/poptimizer/opt/pkg/lgr"
	"go.mongodb.org/mongo-driver/mongo"
)

const _backupDir = `dump`

// BackupHandler обработчик событий, отвечающий за backup пользовательских данных.
type BackupHandler struct {
	logger *lgr.Logger
	pub    domain.Publisher
	uri    string
}

// NewBackupHandler создает обработчик ответственный за бекап данных.
func NewBackupHandler(logger *lgr.Logger, pub domain.Publisher, uri string) *BackupHandler {
	return &BackupHandler{
		logger: logger,
		pub:    pub,
		uri:    uri,
	}
}

// Match фильтрует данные, вводимые пользователем.
func (h BackupHandler) Match(event domain.Event) bool {
	qid := domain.QualifiedID{
		Sub:   port.Subdomain,
		Group: selected.Group,
		ID:    selected.Group,
	}

	return event.QualifiedID == qid
}

// Handle осуществляет бекап данных.
func (h BackupHandler) Handle(ctx context.Context, event domain.Event) {
	if err := clients.MongoDBBackup(ctx, _backupDir, h.uri, port.Subdomain, selected.Group); err != nil {
		event.Data = fmt.Errorf("can't backup data -> %w", err)

		h.pub.Publish(event)

		return
	}

	h.logger.Infof("backup of collection %s.%s completed", port.Subdomain, selected.Group)
}

func (h BackupHandler) String() string {
	return `Handler("backup")`
}

// Инициализирует клиента базы данных и создает коллекции с данными пользователя по умолчанию при их отсутствии.
func prepareDB(ctx context.Context, logger *lgr.Logger, uri string) *mongo.Client {
	client, err := clients.NewMongoClient(uri)
	if err != nil {
		logger.Panicf("can't create MongoDB client -> %s", err)
	}

	count, err := client.Database(port.Subdomain).Collection(selected.Group).EstimatedDocumentCount(ctx)
	if err != nil {
		logger.Panicf("can't check MongoDB data -> %s", err)
	}

	if count != 0 {
		return client
	}

	if err := clients.MongoDBRestore(ctx, _backupDir, uri, port.Subdomain, selected.Group); err != nil {
		logger.Panicf("can't create collection %s.%s -> %s", port.Subdomain, selected.Group, err)
	}

	logger.Infof("collection %s.%s created", port.Subdomain, selected.Group)

	return client
}
