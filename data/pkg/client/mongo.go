package client

import (
	"context"
	"fmt"
	"os/exec"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const _timeout = 30 * time.Second

// NewMongoDB создает клиент и пингует сервер.
func NewMongoDB(uri string) (*mongo.Client, error) {
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

// MongoDBBackUpCmd создает команду для сохранения коллекции.
func MongoDBBackUpCmd(ctx context.Context, folder, uri, db, collection string) *exec.Cmd {
	return exec.CommandContext(
		ctx,
		"mongodump",
		"--out",
		folder,
		"--uri",
		fmt.Sprintf("\"%s\"", uri),
		"--db",
		db,
		"--collection",
		collection,
	)
}

// MongoDBRestoreCmd создает команду для восстановления коллекции.
func MongoDBRestoreCmd(ctx context.Context, folder, uri, db, collection string) *exec.Cmd {
	return exec.CommandContext(
		ctx,
		"mongorestore",
		"--uri",
		fmt.Sprintf("\"%s\"", uri),
		"--db",
		db,
		"--collection",
		collection,
		folder,
	)
}
