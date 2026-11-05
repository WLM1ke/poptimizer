from datetime import date, datetime

import pytest
from pydantic import MongoDsn

from poptimizer.adapters import mongo
from poptimizer.core import domain, errors
from poptimizer.evolve.models import evolve
from poptimizer.runtime import uow


class Doc(domain.Entity):
    value: int = 0
    name: str = ""


_COLLECTION = Doc.__name__
_MODELS = evolve.Model.__name__


def _model_doc(uid: domain.UID, day: datetime, llh: float, alfa: float, duration: float) -> mongo.MongoDocument:
    return {"_id": uid, "ver": 0, "day": day, "llh": llh, "alfa": alfa, "duration": duration}


async def test_save_replaces_only_under_matching_version_and_bumps_it(test_db):
    uid = domain.UID("doc")
    await test_db[_COLLECTION].insert_one({"_id": uid, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    await store.save(Doc(uid=uid, value=5), uow.Version(0))

    assert await test_db[_COLLECTION].find_one({"_id": uid}) == {"_id": uid, "ver": 1, "value": 5, "name": ""}

    with pytest.raises(errors.AdapterError, match="wrong version"):
        await store.save(Doc(uid=uid, value=7), uow.Version(0))

    assert await test_db[_COLLECTION].find_one({"_id": uid}) == {"_id": uid, "ver": 1, "value": 5, "name": ""}


async def test_get_on_missing_singleton_creates_version_zero_document(test_db):
    store = mongo.Store(test_db)

    obj, ver = await store.get(Doc, domain.UID("missing"))

    assert ver == uow.Version(0)
    assert obj == Doc(uid=domain.UID("missing"))
    assert await test_db[_COLLECTION].find_one({"_id": obj.uid}) == {"_id": obj.uid, "ver": 0}


async def test_get_all_yields_detached_entities(test_db):
    await test_db[_COLLECTION].insert_one({"_id": domain.UID("one"), "ver": 0, "value": 1})
    await test_db[_COLLECTION].insert_one({"_id": domain.UID("two"), "ver": 0, "value": 2})
    store = mongo.Store(test_db)

    docs = [obj async for obj in store.get_all(Doc)]

    assert {obj.uid for obj in docs} == {domain.UID("one"), domain.UID("two")}

    one = next(obj for obj in docs if obj.uid == domain.UID("one"))
    one.value = 99

    assert await test_db[_COLLECTION].find_one({"_id": domain.UID("one")}) == {
        "_id": domain.UID("one"),
        "ver": 0,
        "value": 1,
    }


async def test_count_models(test_db):
    store = mongo.Store(test_db)

    assert await store.count_models() == 0

    for n in range(3):
        await test_db[_MODELS].insert_one(_model_doc(domain.UID(f"m{n}"), datetime(2020, 1, 1), 1, 1, 1))

    assert await store.count_models() == 3


async def test_next_model_for_update_picks_from_pareto_front_with_longest_duration(test_db):
    await test_db[_MODELS].insert_one(_model_doc(domain.UID("worse"), datetime(2020, 1, 2), 1, 1, 1))
    await test_db[_MODELS].insert_one(_model_doc(domain.UID("best"), datetime(2020, 1, 1), 2, 2, 9))
    store = mongo.Store(test_db)

    model, ver, longest_duration = await store.next_model_for_update()

    assert model.uid == domain.UID("best")
    assert ver == uow.Version(0)
    assert longest_duration == 9


async def test_delete_worst_model_keeps_at_least_one_and_removes_dominated(test_db):
    store = mongo.Store(test_db)
    assert await store.delete_worst_model() == 0

    uid = domain.UID("only")
    await test_db[_MODELS].insert_one(_model_doc(uid, datetime(2020, 1, 1), 1, 1, 1))

    assert await store.delete_worst_model() == 0
    assert await test_db[_MODELS].find_one({"_id": uid}) is not None

    await test_db[_MODELS].insert_one(_model_doc(domain.UID("worse"), datetime(2020, 1, 2), 0.5, 0.5, 1))

    assert await store.delete_worst_model() == 1
    assert await test_db[_MODELS].find_one({"_id": domain.UID("worse")}) is None
    assert await test_db[_MODELS].find_one({"_id": uid}) is not None


async def test_get_models_returns_models_of_the_given_day(test_db):
    await test_db[_MODELS].insert_one(_model_doc(domain.UID("early"), datetime(2019, 5, 1), 1, 1, 1))
    await test_db[_MODELS].insert_one(_model_doc(domain.UID("late"), datetime(2020, 5, 1), 2, 2, 2))
    store = mongo.Store(test_db)

    models = await store.get_models(date(2019, 5, 1))

    assert [model.uid for model in models] == [domain.UID("early")]


async def test_sample_models_returns_n_distinct_models(test_db):
    uids = {domain.UID(f"m{n}") for n in range(3)}
    for uid in uids:
        await test_db[_MODELS].insert_one(_model_doc(uid, datetime(2020, 1, 1), 1, 1, 1))
    store = mongo.Store(test_db)

    sampled = await store.sample_models(2)

    assert len(sampled) == 2
    assert {model.uid for model in sampled} <= uids


async def test_bson_failures_surface_as_adapter_error(test_db):
    store = mongo.Store(test_db)

    with pytest.raises(errors.AdapterError, match="can't save entities"):
        await store.save(Doc(uid=domain.UID("doc"), name="bad\ud800name"), uow.Version(0))


async def test_driver_failures_surface_as_adapter_error():
    async with mongo.db(MongoDsn("mongodb://localhost:27017"), "poptimizer-test") as closed_db:
        pass
    closed_store = mongo.Store(closed_db)

    with pytest.raises(errors.AdapterError, match="can't load"):
        await closed_store.get(Doc, domain.UID("doc"))


async def test_unprocessable_document_surfaces_as_adapter_error(test_db):
    uid = domain.UID("broken")
    await test_db[_COLLECTION].insert_one({"_id": uid, "ver": 0, "value": "not-an-int"})
    store = mongo.Store(test_db)

    with pytest.raises(errors.AdapterError, match="can't create"):
        await store.get(Doc, uid)
