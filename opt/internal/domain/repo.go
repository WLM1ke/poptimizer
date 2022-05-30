package domain

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
)

var ErrWrongVersion = errors.New("wrong entity version")

// ReadRepo осуществляет загрузку объекта.
type ReadRepo[D any] interface {
	// Get загружает объект.
	Get(ctx context.Context, qid QualifiedID) (Entity[D], error)
}

// ReadWriteRepo осуществляет загрузку и сохранение объекта.
type ReadWriteRepo[D any] interface {
	ReadRepo[D]
	// Save перезаписывает объект.
	Save(ctx context.Context, entity Entity[D]) error
}

// ReadAppendRepo осуществляет загрузку и дополнение данных объекта.
type ReadAppendRepo[D any] interface {
	ReadRepo[D]
	// Append добавляет данные в конец слайса с данными.
	Append(ctx context.Context, entity Entity[D]) error
}

type entityDao[D any] struct {
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
	return &Repo[D]{
		client: db,
	}
}

// Get загружает объект.
func (r *Repo[D]) Get(ctx context.Context, qid QualifiedID) (entity Entity[D], err error) {
	var dao entityDao[D]

	collection := r.client.Database(qid.Sub).Collection(qid.Group)
	err = collection.FindOne(ctx, bson.M{"_id": qid.ID}).Decode(&dao)

	switch {
	case errors.Is(err, mongo.ErrNoDocuments):
		err = nil
		entity = newEmptyEntity[D](qid)
	case err != nil:
		err = fmt.Errorf("can't load %#v -> %w", qid, err)
	default:
		entity = newTable(qid, dao.Ver, dao.Timestamp, dao.Data)
	}

	return entity, err
}

// Save перезаписывает таблицу.
func (r *Repo[D]) Save(ctx context.Context, entity Entity[D]) error {
	if entity.ver == 0 {
		return r.insert(ctx, entity)
	}

	collection := r.client.Database(entity.id.Sub).Collection(entity.id.Group)

	filter := bson.M{
		"_id": entity.id.ID,
		"ver": entity.ver,
	}
	update := bson.M{"$set": bson.M{
		"ver":       entity.ver + 1,
		"timestamp": entity.Timestamp,
		"data":      entity.Data,
	}}

	switch rez, err := collection.UpdateOne(ctx, filter, update); {
	case err != nil:
		return fmt.Errorf("can't replace %#v -> %w", entity.id, err)
	case rez.MatchedCount == 0:
		return fmt.Errorf("can't replace %#v -> %w", entity.id, ErrWrongVersion)
	}

	return nil
}

// Append добавляет строки в конец таблицы.
func (r *Repo[D]) Append(ctx context.Context, entity Entity[D]) error {
	if entity.ver == 0 {
		return r.insert(ctx, entity)
	}

	collection := r.client.Database(entity.id.Sub).Collection(entity.id.Group)

	filter := bson.M{
		"_id": entity.id.ID,
		"ver": entity.ver,
	}
	update := bson.M{
		"$set": bson.M{
			"ver":       entity.ver + 1,
			"timestamp": entity.Timestamp,
		},
		"$push": bson.M{"data": bson.M{"$each": entity.Data}},
	}

	switch rez, err := collection.UpdateOne(ctx, filter, update); {
	case err != nil:
		return fmt.Errorf("can't append %#v -> %w", entity.id, err)
	case rez.MatchedCount == 0:
		return fmt.Errorf("can't append %#v -> %w", entity.id, ErrWrongVersion)
	default:
		return nil
	}
}

func (r *Repo[D]) insert(ctx context.Context, entity Entity[D]) error {
	collection := r.client.Database(entity.id.Sub).Collection(entity.id.Group)

	doc := bson.M{
		"_id":       entity.id.ID,
		"ver":       entity.ver + 1,
		"timestamp": entity.Timestamp,
		"data":      entity.Data,
	}

	switch _, err := collection.InsertOne(ctx, doc); {
	case mongo.IsDuplicateKeyError(err):
		return fmt.Errorf("can't insert %#v -> %w", entity.id, ErrWrongVersion)
	case err != nil:
		return fmt.Errorf("can't insert %#v -> %w", entity.id, err)
	default:
		return nil
	}
}
