package domain

import (
	"context"
	"testing"
	"time"

	"github.com/WLM1ke/poptimizer/opt/pkg/clients"
	"github.com/stretchr/testify/assert"
	"go.mongodb.org/mongo-driver/mongo"
)

func TestRepo_Save(t *testing.T) { //nolint:paralleltest
	client, err := clients.NewMongoClient("mongodb://localhost:27017")
	defer func() {
		assert.Nil(
			t,
			client.Database("test").Drop(context.Background()),
			"can't drop test db -> %s",
			err,
		)
	}()

	assert.Nil(t, err, "can't connect to test MongoDB -> %s", err)

	repo := NewRepo[int](client)
	qid := QID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	agg, err := repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get new agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 0, agg.ver, "incorrect version for new agg")
	assert.Equal(t, time.Time{}, agg.Timestamp, "incorrect timestamp in new agg")
	assert.Equal(t, 0, agg.Entity, "incorrect data in new agg")

	now := time.Now().UTC().Truncate(time.Second)

	agg.Timestamp = now
	agg.Entity = 42

	assert.Nil(t, repo.Save(context.Background(), agg), "can't save agg -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), agg),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	agg, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 1, agg.ver, "incorrect version for saved agg")
	assert.Equal(t, now, agg.Timestamp, "incorrect timestamp in saved agg")
	assert.Equal(t, 42, agg.Entity, "incorrect data in saved agg")

	now = time.Now().UTC().Truncate(time.Hour)

	agg.Timestamp = now
	agg.Entity = 43

	assert.Nil(t, repo.Save(context.Background(), agg), "can't save agg -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), agg),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	agg, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 2, agg.ver, "incorrect version for saved agg")
	assert.Equal(t, now, agg.Timestamp, "incorrect timestamp in saved agg")
	assert.Equal(t, 43, agg.Entity, "incorrect data in saved agg")
}

func TestRepo_Append(t *testing.T) { //nolint:paralleltest
	client, err := clients.NewMongoClient("mongodb://localhost:27017")
	defer func() {
		assert.Nil(
			t,
			client.Database("test").Drop(context.Background()),
			"can't drop db client -> %s",
			err,
		)
	}()

	assert.Nil(t, err, "can't connect to test MongoDB -> %s", err)

	repo := NewRepo[[]int](client)
	qid := QID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	agg, err := repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get new agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 0, agg.ver, "incorrect version for new agg")
	assert.Equal(t, time.Time{}, agg.Timestamp, "incorrect timestamp in new agg")
	assert.Equal(t, 0, len(agg.Entity), "incorrect data in new agg")

	now := time.Now().UTC().Truncate(time.Second)

	agg.Timestamp = now
	agg.Entity = []int{42}

	assert.Nil(t, repo.Append(context.Background(), agg), "can't save agg -> %s", err)
	assert.ErrorIs(
		t,
		repo.Save(context.Background(), agg),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	agg, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 1, agg.ver, "incorrect version for saved agg")
	assert.Equal(t, now, agg.Timestamp, "incorrect timestamp in saved agg")
	assert.Equal(t, []int{42}, agg.Entity, "incorrect data in saved agg")

	now = time.Now().UTC().Truncate(time.Hour)

	agg.Timestamp = now
	agg.Entity = []int{43}

	assert.Nil(t, repo.Append(context.Background(), agg), "can't save agg -> %s", err)
	assert.ErrorIs(
		t,
		repo.Append(context.Background(), agg),
		ErrWrongVersion,
		"error in optimistic concurrency control",
	)

	agg, err = repo.Get(context.Background(), qid)
	assert.Nil(t, err, "can't get saved agg -> %s", err)

	assert.Equal(t, qid, agg.id, "incorrect id")
	assert.Equal(t, 2, agg.ver, "incorrect version for saved agg")
	assert.Equal(t, now, agg.Timestamp, "incorrect timestamp in saved agg")
	assert.Equal(t, []int{42, 43}, agg.Entity, "incorrect data in saved agg")
}

func TestRepo_GetGroup(t *testing.T) { //nolint:paralleltest
	client, err := clients.NewMongoClient("mongodb://localhost:27017")
	defer func() {
		assert.Nil(
			t,
			client.Database("test").Drop(context.Background()),
			"can't drop db client -> %s",
			err,
		)
	}()

	assert.Nil(t, err, "can't connect to test MongoDB -> %s", err)

	repo := NewRepo[int](client)

	aggs, err := repo.GetGroup(context.Background(), "test", "some")
	assert.Nil(t, err, "can't get new agg -> %s", err)

	assert.Empty(t, aggs, "should be no aggregates")

	qid1 := QID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	agg1 := newEmptyAggregate[int](qid1)
	agg1.Timestamp = time.Now().UTC().Truncate(time.Millisecond)
	agg1.Entity = 42

	err = repo.Save(context.Background(), agg1)
	assert.Nil(t, err, "can't save test data")

	qid2 := QID{
		Sub:   "test",
		Group: "some",
		ID:    "number2",
	}

	agg2 := newEmptyAggregate[int](qid2)
	agg2.Timestamp = time.Now().UTC().Truncate(time.Millisecond)
	agg2.Entity = 44

	err = repo.Save(context.Background(), agg2)
	assert.Nil(t, err, "can't save test data")

	agg2, err = repo.Get(context.Background(), qid2)
	assert.Nil(t, err, "can't prepare test data")

	err = repo.Save(context.Background(), agg2)
	assert.Nil(t, err, "can't save test data")

	aggs, err = repo.GetGroup(context.Background(), "test", "some")
	assert.Nil(t, err, "can't load from repo")

	agg1.ver = 1
	agg2.ver = 2

	assert.ElementsMatch(t, []Aggregate[int]{agg1, agg2}, aggs, "wrong aggregates")
}

func TestRepo_Errors(t *testing.T) {
	t.Parallel()

	var client mongo.Client

	repo := NewRepo[int](&client)
	qid := QID{
		Sub:   "test",
		Group: "some",
		ID:    "number",
	}

	_, err := repo.Get(context.Background(), qid)
	assert.ErrorContains(t, err, "can't load", "no error on loading from bad db")

	_, err = repo.GetGroup(context.Background(), qid.Sub, qid.Group)
	assert.ErrorContains(t, err, "can't load", "no error on loading from bad db")

	agg := Aggregate[int]{ver: 0}
	err = repo.Save(context.Background(), agg)
	assert.ErrorContains(t, err, "can't insert", "no error on loading from bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on loading from bad db")

	err = repo.Append(context.Background(), agg)
	assert.ErrorContains(t, err, "can't insert", "no error on inserting in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on inserting in bad db")

	agg = Aggregate[int]{ver: 1}
	err = repo.Save(context.Background(), agg)
	assert.ErrorContains(t, err, "can't replace", "no error on replacing in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on replacing in bad db")

	err = repo.Append(context.Background(), agg)
	assert.ErrorContains(t, err, "can't append", "no error on appending in bad db")
	assert.NotErrorIs(t, err, ErrWrongVersion, "no error on appending in bad db")
}
