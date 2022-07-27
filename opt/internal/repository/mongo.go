package repository

import (
	"context"
	"errors"
	"fmt"

	"github.com/WLM1ke/poptimizer/opt/internal/domain"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// ErrWrongVersion ошибка попытки записи неверной версии агрегата в рамках optimistic concurrency control.
var ErrWrongVersion = errors.New("wrong agg version")

// Mongo обеспечивает хранение и загрузку доменных объектов.
type Mongo[E domain.Entity] struct {
	client *mongo.Client
}

// NewMongo - создает новый репозиторий на основе MongoDB.
func NewMongo[E domain.Entity](client *mongo.Client) *Mongo[E] {
	return &Mongo[E]{
		client: client,
	}
}

// Get загружает объект.
func (r *Mongo[E]) Get(ctx context.Context, qid domain.QID) (agg domain.Aggregate[E], err error) {
	var dao aggDAO[E]

	collection := getCollection(r.client, qid)
	err = collection.FindOne(ctx, bson.M{"_id": qid.ID}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		err = nil
		agg = newEmptyAggregate[E](qid)
	case err != nil:
		err = fmt.Errorf("can't load %#v -> %w", qid, err)
	default:
		agg = newAggregate(qid, dao)
	}

	return agg, err
}

func (r *Mongo[E]) List(ctx context.Context, sub, group string) ([]string, error) {
	var results []bson.M

	collection := r.client.Database(sub).Collection(group)
	projection := options.Find().SetProjection(bson.M{"_id": 1})

	cursor, err := collection.Find(ctx, bson.D{}, projection)
	if err != nil {
		return nil, fmt.Errorf("can't load %s.%s -> %w", sub, group, err)
	}

	if err := cursor.All(ctx, &results); err != nil {
		return nil, fmt.Errorf("can't decode %s.%s -> %w", sub, group, err)
	}

	qids := make([]string, 0, len(results))

	for n := range results {
		qid, ok := results[n]["_id"].(string)
		if !ok {
			return nil, fmt.Errorf("can't decode %s.%s -> %w", sub, group, err)
		}

		qids = append(qids, qid)
	}

	return qids, nil
}

func (r *Mongo[E]) GetGroup(ctx context.Context, sub, group string) ([]domain.Aggregate[E], error) {
	var allDAO []aggDAO[E]

	collection := r.client.Database(sub).Collection(group)

	cursor, err := collection.Find(ctx, bson.D{})
	if err != nil {
		return nil, fmt.Errorf("can't load %s.%s -> %w", sub, group, err)
	}

	if err := cursor.All(ctx, &allDAO); err != nil {
		return nil, fmt.Errorf("can't decode %s.%s -> %w", sub, group, err)
	}

	aggs := make([]domain.Aggregate[E], 0, len(allDAO))

	for _, dao := range allDAO {
		qid := domain.QID{
			Sub:   sub,
			Group: group,
			ID:    dao.ID,
		}

		aggs = append(aggs, newAggregate(qid, dao))
	}

	return aggs, nil
}

// Save перезаписывает таблицу.
func (r *Mongo[E]) Save(ctx context.Context, agg domain.Aggregate[E]) error {
	if agg.Ver() == 0 {
		return r.insert(ctx, agg)
	}

	collection := getCollection(r.client, agg.QID())

	filter := bson.M{
		"_id": agg.QID().ID,
		"ver": agg.Ver(),
	}
	update := bson.M{"$set": bson.M{
		"ver":       agg.Ver() + 1,
		"timestamp": agg.Timestamp(),
		"data":      agg.Entity(),
	}}

	switch rez, err := collection.UpdateOne(ctx, filter, update); {
	case err != nil:
		return fmt.Errorf("can't replace %#v -> %w", agg.QID(), err)
	case rez.MatchedCount == 0:
		return fmt.Errorf("can't replace %#v -> %w", agg.QID(), ErrWrongVersion)
	}

	return nil
}

func (r *Mongo[E]) insert(ctx context.Context, agg domain.Aggregate[E]) error {
	collection := getCollection(r.client, agg.QID())

	doc := bson.M{
		"_id":       agg.QID().ID,
		"ver":       agg.Ver() + 1,
		"timestamp": agg.Timestamp(),
		"data":      agg.Entity(),
	}

	switch _, err := collection.InsertOne(ctx, doc); {
	case mongo.IsDuplicateKeyError(err):
		return fmt.Errorf("can't insert %#v -> %w", agg.QID(), ErrWrongVersion)
	case err != nil:
		return fmt.Errorf("can't insert %#v -> %w", agg.QID(), err)
	default:
		return nil
	}
}

func (r Mongo[E]) Delete(ctx context.Context, qid domain.QID) error {
	collection := getCollection(r.client, qid)

	filter := bson.M{
		"_id": qid.ID,
	}

	_, err := collection.DeleteOne(ctx, filter)
	if err != nil {
		return fmt.Errorf("can't delete %#v -> %w", qid, err)
	}

	return nil
}

// MongoJSON обеспечивает хранение и загрузку таблиц.
type MongoJSON struct {
	client *mongo.Client
}

// NewMongoJSON - создает новый репозиторий на основе MongoDB.
func NewMongoJSON(client *mongo.Client) *MongoJSON {
	return &MongoJSON{
		client: client,
	}
}

// GetJSON загружает ExtendedJSON представление данных.
func (r *MongoJSON) GetJSON(ctx context.Context, qid domain.QID) ([]byte, error) {
	collection := getCollection(r.client, qid)

	projections := options.FindOne().SetProjection(bson.M{"_id": 0, "data": 1})

	rawData, err := collection.FindOne(ctx, bson.M{"_id": qid.ID}, projections).DecodeBytes()

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		return nil, fmt.Errorf("data not found: %#v", qid)
	case err != nil:
		return nil, fmt.Errorf("can't load data %#v -> %w", qid, err)
	}

	json, err := bson.MarshalExtJSON(rawData, true, true)
	if err != nil {
		return nil, fmt.Errorf("can't prepare json %#v -> %w", qid, err)
	}

	return json, nil
}

func getCollection(client *mongo.Client, qid domain.QID) *mongo.Collection {
	return client.Database(qid.Sub).Collection(qid.Group)
}