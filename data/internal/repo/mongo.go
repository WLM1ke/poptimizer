package repo

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type tableDAO[R domain.Row] struct {
	Name domain.Name `bson:"_id"`
	Date time.Time   `bson:"date"`
	Rows []R         `bson:"rows"`
}

// Mongo обеспечивает хранение и загрузку таблиц.
type Mongo[R domain.Row] struct {
	db *mongo.Database
}

// NewMongo - создает новый репозиторий на основе MongoDB.
func NewMongo[R domain.Row](db *mongo.Database) *Mongo[R] {
	return &Mongo[R]{
		db: db,
	}
}

// Get загружает таблицу.
func (r *Mongo[R]) Get(ctx context.Context, tableID domain.ID) (table domain.Table[R], err error) {
	var dao tableDAO[R]

	collection := r.db.Collection(string(tableID.Group()))
	err = collection.FindOne(ctx, bson.M{"_id": string(tableID.Name())}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		err = nil
		table = domain.NewEmptyTable[R](tableID)
	case err != nil:
		err = fmt.Errorf("%w: %#v -> %s", ErrInternal, tableID, err)
	default:
		table = domain.NewTable(tableID, dao.Date, dao.Rows)
	}

	return table, err
}

// Replace перезаписывает таблицу.
func (r *Mongo[R]) Replace(ctx context.Context, table domain.Table[R]) error {
	collection := r.db.Collection(string(table.Group()))

	filter := bson.M{"_id": table.Name()}
	update := bson.M{"$set": bson.M{"rows": table.Rows(), "date": table.Date()}}

	if _, err := collection.UpdateOne(ctx, filter, update, options.Update().SetUpsert(true)); err != nil {
		return fmt.Errorf("%w: %#v -> %s", ErrInternal, table.ID(), err)
	}

	return nil
}

// Append добавляет строки в конец таблицы.
func (r *Mongo[R]) Append(ctx context.Context, table domain.Table[R]) error {
	collection := r.db.Collection(string(table.Group()))

	filter := bson.M{"_id": table.Name()}
	update := bson.M{"$push": bson.M{"rows": bson.M{"$each": table.Rows()}}, "$set": bson.M{"date": table.Date()}}

	if _, err := collection.UpdateOne(ctx, filter, update, options.Update().SetUpsert(true)); err != nil {
		return fmt.Errorf("%w: %#v -> %s", ErrInternal, table.ID(), err)
	}

	return nil
}

// MongoJSON обеспечивает хранение и загрузку таблиц.
type MongoJSON struct {
	db *mongo.Database
}

// NewMongoJSON - создает новый репозиторий на основе MongoDB.
func NewMongoJSON(db *mongo.Database) *MongoJSON {
	return &MongoJSON{
		db: db,
	}
}

// GetJSON загружает ExtendedJSON представление таблицы.
func (r *MongoJSON) GetJSON(ctx context.Context, tableID domain.ID) ([]byte, error) {
	collection := r.db.Collection(string(tableID.Group()))

	projections := options.FindOne().SetProjection(bson.M{"_id": 0, "rows": 1})

	raw, err := collection.FindOne(ctx, bson.M{"_id": tableID.Name()}, projections).DecodeBytes()

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		return nil, fmt.Errorf("%w: %#v", ErrTableNotFound, tableID)
	case err != nil:
		return nil, fmt.Errorf("%w: %#v -> %s", ErrInternal, tableID, err)
	}

	json, err := bson.MarshalExtJSON(raw, true, true)
	if err != nil {
		return nil, fmt.Errorf("%w: %#v -> %s", ErrInternal, tableID, err)
	}

	return json, nil
}
