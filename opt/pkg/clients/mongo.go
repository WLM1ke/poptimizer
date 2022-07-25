package clients

import (
	"context"
	"fmt"
	"os/exec"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const _timeout = 30 * time.Second

// NewMongoClient создает клиент и пингует сервер.
func NewMongoClient(uri string) (*mongo.Client, error) {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	opt := options.Client().ApplyURI(uri)

	client, err := mongo.Connect(ctx, opt)
	if err != nil {
		return nil, fmt.Errorf("can't start MongoDB client -> %w", err)
	}

	err = client.Ping(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("can't ping MongoDB server -> %w", err)
	}

	return client, nil
}

// MongoDBBackup создает команду для сохранения коллекции.
func MongoDBBackup(ctx context.Context, folder, uri, database, collection string) error {
	err := exec.CommandContext(
		ctx,
		"mongodump",
		"--out",
		folder,
		"--uri",
		fmt.Sprintf("%q", uri),
		"--db",
		database,
		"--collection",
		collection,
	).Run()
	if err != nil {
		err = fmt.Errorf(
			"can't back up %s collection -> %w",
			fmt.Sprintf("%s.%s", database, collection),
			err,
		)
	}

	return err
}

// MongoDBRestore создает команду для восстановления коллекции.
func MongoDBRestore(ctx context.Context, folder, uri, database, collection string) error {
	collection = fmt.Sprintf("%s.%s", database, collection)

	err := exec.CommandContext(
		ctx,
		"mongorestore",
		"--uri",
		fmt.Sprintf("%q", uri),
		"--nsInclude",
		collection,
		folder,
	).Run()
	if err != nil {
		err = fmt.Errorf(
			"can't restore %s collection -> %w",
			collection,
			err,
		)
	}

	return err
}
