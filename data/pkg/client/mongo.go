package client

import (
	"context"
	"fmt"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"time"
)

const _timeout = 30 * time.Second

func MongoDB(uri, db string) *mongo.Database {
	ctx, cancel := context.WithTimeout(context.Background(), _timeout)
	defer cancel()

	opt := options.Client().ApplyURI(uri)
	client, err := mongo.Connect(ctx, opt)
	if err != nil {
		panic(fmt.Sprintf("can't start MongoDB client -> %s", err))
	}

	err = client.Ping(ctx, nil)
	if err != nil {
		panic(fmt.Sprintf("can't ping MongoDB server -> %s", err))
	}

	return client.Database(db)
}
