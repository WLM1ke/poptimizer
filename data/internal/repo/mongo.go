package repo

import (
	"context"
	"errors"
	"fmt"
	"github.com/WLM1ke/poptimizer/data/internal/domain"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"time"
)

type tableDAO [R]struct {
	Name domain.Name `bson:"_id"`
	Date time.Time   `bson:"date"`
	Rows []R         `bson:"rows"`
}

func NewTableDAO[R comparable](table domain.Table[R]) tableDAO[R] {
	return tableDAO[R]{
		Name: table.Name(),
		Date: table.Date(),
		Rows: table.Rows,
	}
}

func (d tableDAO[R]) toTable(id domain.ID) domain.Table[R] {
	return domain.Table[R]{
		Version: domain.NewVersion(id, d.Date),
		Rows:    d.Rows,
	}
}

// Mongo обеспечивает хранение и загрузку таблиц.
type Mongo[R comparable] struct {
	db *mongo.Database
}

// NewMongo - создает новый репозиторий на основе MongoDB.
func NewMongo[R comparable](db *mongo.Database) *Mongo[R] {
	return &Mongo[R]{
		db: db,
	}
}

// Get загружает таблицу.
func (r *Mongo[R]) Get(ctx context.Context, id domain.ID) (domain.Table[R], error) {
	var dao tableDAO[R]

	collection := r.db.Collection(string(id.Group()))
	err := collection.FindOne(ctx, bson.M{"_id": string(id.Name())}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		return nil, fmt.Errorf(
			"%w: %s", ErrTableNotFound, id)
	case err != nil:
		return nil, fmt.Errorf("%w: %#v - %s", ErrInternal, id, err)
	}

	return dao.toTable(id), nil
}

// Replace перезаписывает таблицу.
func (r *Mongo[R]) Replace(ctx context.Context, table domain.Table[R]) error {
	collection := r.db.Collection(string(table.Group()))

	filter := bson.M{"_id": table.Name}
	update := bson.M{"$set": bson.M{"rows": table.Rows, "date": table.Date}}

	if _, err := collection.UpdateOne(ctx, filter, update, options.Update().SetUpsert(true)); err != nil {
		return fmt.Errorf("%w: %#v - %s", ErrTableUpdate, table, err)
	}

	return nil
}

// Append добавляет строки в конец таблицы.
func (r *Mongo[R]) Append(ctx context.Context, table domain.Table[R]) error {
	collection := r.db.Collection(string(table.Group()))

	filter := bson.M{"_id": table.Name}
	update := bson.M{"$push": bson.M{"rows": bson.M{"$each": table.Rows}}}

	if _, err := collection.UpdateOne(ctx, filter, update, options.Update().SetUpsert(true)); err != nil {
		return fmt.Errorf("%w: %#v - %s", ErrTableUpdate, table, err)
	}

	return nil
}

// GetJSON загружает ExtendedJSON представление таблицы.
func (r *Mongo[R]) GetJSON(ctx context.Context, id domain.ID) ([]byte, error) {
	collection := r.db.Collection(string(id.Group()))

	projections := options.FindOne().SetProjection(bson.M{"_id": 0, "rows": 1, "date": 1})

	raw, err := collection.FindOne(ctx, bson.M{"_id": id.Name}, projections).DecodeBytes()
	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		return nil, fmt.Errorf("%w: %s", ErrTableNotFound, id)
	case err != nil:
		return nil, fmt.Errorf("%w: %#v - %s", ErrInternal, id, err)
	}

	json, err := bson.MarshalExtJSON(raw, true, true)
	if err != nil {
		return nil, fmt.Errorf("%w: %#v - %s", ErrInternal, id, err)
	}

	return json, nil
}
