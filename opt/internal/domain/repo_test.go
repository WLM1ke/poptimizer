package domain

import (
	"context"
	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/stretchr/testify/assert"
	"go.mongodb.org/mongo-driver/mongo"
	"testing"
	"time"
)

func TestRepoSave(t *testing.T) {
	db, err := clients.NewMongoClient("mongodb://localhost:27017")
	assert.Nil(t, err, "can't connect to test MongoDB -> %s", err)
	defer func() {
		assert.Nil(
			t,
			db.Database("test").Drop(context.Background()),
			"can't drop test db -> %s",
			err,
		)
	}()

	repo := NewRepo[int](db)
	qid := QualifiedID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	entity, err := repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get new entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 0, entity.ver, "incorrect version for new entity")
	assert.Equal(t, time.Time{}, entity.Timestamp, "incorrect timestamp in new entity")
	assert.Equal(t, 0, entity.Data, "incorrect data in new entity")

	now := time.Now().UTC().Truncate(time.Second)

	entity.Timestamp = now
	entity.Data = 42

	assert.Nil(t, repo.Save(context.Background(), entity), "can't save entity -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), entity),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	entity, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 1, entity.ver, "incorrect version for saved entity")
	assert.Equal(t, now, entity.Timestamp, "incorrect timestamp in saved entity")
	assert.Equal(t, 42, entity.Data, "incorrect data in saved entity")

	now = time.Now().UTC().Truncate(time.Hour)

	entity.Timestamp = now
	entity.Data = 43

	assert.Nil(t, repo.Save(context.Background(), entity), "can't save entity -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), entity),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	entity, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 2, entity.ver, "incorrect version for saved entity")
	assert.Equal(t, now, entity.Timestamp, "incorrect timestamp in saved entity")
	assert.Equal(t, 43, entity.Data, "incorrect data in saved entity")
}

func TestRepoAppend(t *testing.T) {
	db, err := clients.NewMongoClient("mongodb://localhost:27017")
	assert.Nil(t, err, "can't connect to test MongoDB -> %s", err)
	defer func() {
		assert.Nil(
			t,
			db.Database("test").Drop(context.Background()),
			"can't drop test db -> %s",
			err,
		)
	}()

	repo := NewRepo[[]int](db)
	qid := QualifiedID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	entity, err := repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get new entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 0, entity.ver, "incorrect version for new entity")
	assert.Equal(t, time.Time{}, entity.Timestamp, "incorrect timestamp in new entity")
	assert.Equal(t, 0, len(entity.Data), "incorrect data in new entity")

	now := time.Now().UTC().Truncate(time.Second)

	entity.Timestamp = now
	entity.Data = []int{42}

	assert.Nil(t, repo.Append(context.Background(), entity), "can't save entity -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), entity),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	entity, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 1, entity.ver, "incorrect version for saved entity")
	assert.Equal(t, now, entity.Timestamp, "incorrect timestamp in saved entity")
	assert.Equal(t, []int{42}, entity.Data, "incorrect data in saved entity")

	now = time.Now().UTC().Truncate(time.Hour)

	entity.Timestamp = now
	entity.Data = []int{43}

	assert.Nil(t, repo.Append(context.Background(), entity), "can't save entity -> %s", err)
	assert.ErrorIs(
		t,
		repo.Append(context.Background(), entity),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	entity, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved entity -> %s", err)

	assert.Equal(t, qid, entity.id, "incorrect id")
	assert.Equal(t, 2, entity.ver, "incorrect version for saved entity")
	assert.Equal(t, now, entity.Timestamp, "incorrect timestamp in saved entity")
	assert.Equal(t, []int{42, 43}, entity.Data, "incorrect data in saved entity")
}

func TestRepoErrors(t *testing.T) {
	var db mongo.Client

	repo := NewRepo[int](&db)
	qid := QualifiedID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	_, err := repo.Get(context.Background(), qid)
	assert.ErrorContains(t, err, "can't load", "no error on loading from bad db")

	entity := Entity[int]{ver: 0}
	err = repo.Save(context.Background(), entity)
	assert.ErrorContains(t, err, "can't insert", "no error on loading from bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on loading from bad db")

	err = repo.Append(context.Background(), entity)
	assert.ErrorContains(t, err, "can't insert", "no error on inserting in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on inserting in bad db")

	entity = Entity[int]{ver: 1}
	err = repo.Save(context.Background(), entity)
	assert.ErrorContains(t, err, "can't replace", "no error on replacing in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on replacing in bad db")

	err = repo.Append(context.Background(), entity)
	assert.ErrorContains(t, err, "can't append", "no error on appending in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on appending in bad db")
}
