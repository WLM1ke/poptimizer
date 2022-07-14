package domain

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type aggDao[E Entity] struct {
	ID        string    `bson:"_id"`
	Ver       int       `bson:"ver"`
	Timestamp time.Time `bson:"timestamp"`
	Data      E         `bson:"data"`
}

// Repo обеспечивает хранение и загрузку доменных объектов.
type Repo[E Entity] struct {
	client *mongo.Client
}

// NewRepo - создает новый репозиторий на основе MongoDB.
func NewRepo[E Entity](db *mongo.Client) *Repo[E] {
	return &Repo[E]{
		client: db,
	}
}

// Get загружает объект.
func (r *Repo[E]) Get(ctx context.Context, qid QID) (agg Aggregate[E], err error) {
	var dao aggDao[E]

	collection := r.client.Database(qid.Sub).Collection(qid.Group)
	err = collection.FindOne(ctx, bson.M{"_id": qid.ID}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		err = nil
		agg = newEmptyAggregate[E](qid)
	case err != nil:
		err = fmt.Errorf("can't load %#v -> %w", qid, err)
	default:
		agg = newAggregate(qid, dao.Ver, dao.Timestamp, dao.Data)
	}

	return agg, err
}

func (r *Repo[E]) List(ctx context.Context, sub, group string) ([]string, error) {
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

func (r *Repo[E]) GetGroup(ctx context.Context, sub, group string) ([]Aggregate[E], error) {
	var allDAO []aggDao[E]

	collection := r.client.Database(sub).Collection(group)

	cursor, err := collection.Find(ctx, bson.D{})
	if err != nil {
		return nil, fmt.Errorf("can't load %s.%s -> %w", sub, group, err)
	}

	if err := cursor.All(ctx, &allDAO); err != nil {
		return nil, fmt.Errorf("can't decode %s.%s -> %w", sub, group, err)
	}

	aggs := make([]Aggregate[E], 0, len(allDAO))

	for _, dao := range allDAO {
		qid := QID{
			Sub:   sub,
			Group: group,
			ID:    dao.ID,
		}

		aggs = append(aggs, newAggregate(qid, dao.Ver, dao.Timestamp, dao.Data))
	}

	return aggs, nil
}

// Save перезаписывает таблицу.
func (r *Repo[E]) Save(ctx context.Context, agg Aggregate[E]) error {
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
func (r *Repo[E]) Append(ctx context.Context, agg Aggregate[E]) error {
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

func (r *Repo[E]) insert(ctx context.Context, agg Aggregate[E]) error {
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

func (r Repo[E]) Delete(ctx context.Context, qid QID) error {
	collection := r.client.Database(qid.Sub).Collection(qid.Group)

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
func (r *MongoJSON) GetJSON(ctx context.Context, qid QID) ([]byte, error) {
	collection := r.client.Database(qid.Sub).Collection(qid.Group)

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
