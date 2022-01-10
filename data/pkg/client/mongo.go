package client

import (
	"context"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"time"
)

const _timeout = 30 * time.Second

func MongoDB(uri string, db string) *mongo.Database {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		panic("can't start MongoDb client")
	}

	err = client.Ping(ctx, nil)
	if err != nil {
		panic("can't ping MongoDb server")
	}

	return client.Database(db)
}
