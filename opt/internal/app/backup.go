package app

import (
	"context"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"github.com/WLM1ke/poptimizer/opt/internal/domain/data/raw"
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
	if !(event.QualifiedID == securities.GroupID() || event.QualifiedID == raw.ID(event.QualifiedID.ID)) {
		return false
	}

	_, ok := event.Data.(error)

	return !ok
}

func (h BackupHandler) String() string {
	return `securities or raw dividends -> backup`
}

// Handle осуществляет бекап данных.
func (h BackupHandler) Handle(ctx context.Context, event domain.Event) {
	database := event.Sub
	collection := event.Group

	if err := clients.MongoDBBackup(ctx, _backupDir, h.uri, database, collection); err != nil {
		event.Data = fmt.Errorf("can't backup %s.%s -> %w", database, collection, err)

		h.pub.Publish(event)

		return
	}

	h.logger.Infof("backup of %s.%s completed", database, collection)
}

// Инициализирует клиента базы данных и создает коллекции с данными пользователя по умолчанию при их отсутствии.
func prepareDB(ctx context.Context, logger *lgr.Logger, uri string) *mongo.Client {
	client, err := clients.NewMongoClient(uri)
	if err != nil {
		logger.Panicf("can't create MongoDB client -> %s", err)
	}

	for _, qid := range []domain.QualifiedID{securities.GroupID(), raw.ID("")} {
		database := qid.Sub
		collection := qid.Group

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
	}

	return client
}
