package domain

import (
	"context"
	"encoding/gob"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

// ErrWrongVersion ошибка попытки записи неверной версии агрегата в рамках optimistic concurrency control.
var ErrWrongVersion = errors.New("wrong agg version")

// ReadRepo осуществляет загрузку объекта.
type ReadRepo[D any] interface {
	// Get загружает объект.
	Get(ctx context.Context, qid QualifiedID) (Aggregate[D], error)
}

// ReadWriteRepo осуществляет загрузку и сохранение объекта.
type ReadWriteRepo[D any] interface {
	ReadRepo[D]
	// Save перезаписывает объект.
	Save(ctx context.Context, agg Aggregate[D]) error
}

// ReadAppendRepo осуществляет загрузку и дополнение данных объекта.
type ReadAppendRepo[D any] interface {
	ReadRepo[D]
	// Append добавляет данные в конец слайса с данными.
	Append(ctx context.Context, agg Aggregate[D]) error
}

type aggDao[D any] struct {
	ID        string    `bson:"_id"`
	Ver       int       `bson:"ver"`
	Timestamp time.Time `bson:"timestamp"`
	Data      D         `bson:"data"`
}

// Repo обеспечивает хранение и загрузку доменных объектов.
type Repo[D any] struct {
	client *mongo.Client
}

// NewRepo - создает новый репозиторий на основе MongoDB.
func NewRepo[D any](db *mongo.Client) *Repo[D] {
	gob.Register(newEmptyAggregate[D](QualifiedID{}))

	return &Repo[D]{
		client: db,
	}
}

// Get загружает объект.
func (r *Repo[D]) Get(ctx context.Context, qid QualifiedID) (agg Aggregate[D], err error) {
	var dao aggDao[D]

	collection := r.client.Database(qid.Sub).Collection(qid.Group)
	err = collection.FindOne(ctx, bson.M{"_id": qid.ID}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		err = nil
		agg = newEmptyAggregate[D](qid)
	case err != nil:
		err = fmt.Errorf("can't load %#v -> %w", qid, err)
	default:
		agg = newAggregate(qid, dao.Ver, dao.Timestamp, dao.Data)
	}

	return agg, err
}

// Save перезаписывает таблицу.
func (r *Repo[D]) Save(ctx context.Context, agg Aggregate[D]) error {
	if agg.ver == 0 {
		return r.insert(ctx, agg)
	}

	collection := r.client.Database(agg.id.Sub).Collection(agg.id.Group)

	filter := bson.M{
		"_id": agg.id.ID,
		"ver": agg.ver,
	}
	update := bson.M{"$set": bson.M{
		"ver":       agg.ver + 1,
		"timestamp": agg.Timestamp,
		"data":      agg.Entity,
	}}

	switch rez, err := collection.UpdateOne(ctx, filter, update); {
	case err != nil:
		return fmt.Errorf("can't replace %#v -> %w", agg.id, err)
	case rez.MatchedCount == 0:
		return fmt.Errorf("can't replace %#v -> %w", agg.id, ErrWrongVersion)
	}

	return nil
}

// Append добавляет строки в конец таблицы.
func (r *Repo[D]) Append(ctx context.Context, agg Aggregate[D]) error {
	if agg.ver == 0 {
		return r.insert(ctx, agg)
	}

	collection := r.client.Database(agg.id.Sub).Collection(agg.id.Group)

	filter := bson.M{
		"_id": agg.id.ID,
		"ver": agg.ver,
	}
	update := bson.M{
		"$set": bson.M{
			"ver":       agg.ver + 1,
			"timestamp": agg.Timestamp,
		},
		"$push": bson.M{"data": bson.M{"$each": agg.Entity}},
	}

	switch rez, err := collection.UpdateOne(ctx, filter, update); {
	case err != nil:
		return fmt.Errorf("can't append %#v -> %w", agg.id, err)
	case rez.MatchedCount == 0:
		return fmt.Errorf("can't append %#v -> %w", agg.id, ErrWrongVersion)
	default:
		return nil
	}
}

func (r *Repo[D]) insert(ctx context.Context, agg Aggregate[D]) error {
	collection := r.client.Database(agg.id.Sub).Collection(agg.id.Group)

	doc := bson.M{
		"_id":       agg.id.ID,
		"ver":       agg.ver + 1,
		"timestamp": agg.Timestamp,
		"data":      agg.Entity,
	}

	switch _, err := collection.InsertOne(ctx, doc); {
	case mongo.IsDuplicateKeyError(err):
		return fmt.Errorf("can't insert %#v -> %w", agg.id, ErrWrongVersion)
	case err != nil:
		return fmt.Errorf("can't insert %#v -> %w", agg.id, err)
	default:
		return nil
	}
}
