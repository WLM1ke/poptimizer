package app

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/securities"
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
	return event.QualifiedID == securities.ID()
}

func (h BackupHandler) String() string {
	return `securities -> backup`
}

// Handle осуществляет бекап данных.
func (h BackupHandler) Handle(ctx context.Context, event domain.Event) {
	database := data.Subdomain
	collection := securities.ID().Group

	if err := clients.MongoDBBackup(ctx, _backupDir, h.uri, database, collection); err != nil {
		event.Data = fmt.Errorf("can't backup data -> %w", err)

		h.pub.Publish(event)

		return
	}

	h.logger.Infof("backup of collection %s.%s completed", database, collection)
}

// Инициализирует клиента базы данных и создает коллекции с данными пользователя по умолчанию при их отсутствии.
func prepareDB(ctx context.Context, logger *lgr.Logger, uri string) *mongo.Client {
	client, err := clients.NewMongoClient(uri)
	if err != nil {
		logger.Panicf("can't create MongoDB client -> %s", err)
	}

	database := data.Subdomain
	collection := securities.ID().Group

	count, err := client.Database(database).Collection(collection).EstimatedDocumentCount(ctx)
	if err != nil {
		logger.Panicf("can't check MongoDB data -> %s", err)
	}

	if count != 0 {
		return client
	}

	if err := clients.MongoDBRestore(ctx, _backupDir, uri, database, collection); err != nil {
		logger.Panicf("can't create collection %s.%s -> %s", database, collection, err)
	}

	logger.Infof("collection %s.%s created", database, collection)

	return client
}
