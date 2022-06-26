package domain

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
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
