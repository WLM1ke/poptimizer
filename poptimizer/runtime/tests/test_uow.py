import pytest

from poptimizer.adapters import mongo
from poptimizer.core import domain, errors
from poptimizer.runtime import uow


class Doc(domain.Entity):
    value: int = 0


UID = domain.UID("doc")
COLLECTION = Doc.__name__


async def test_document_loads_once_per_uow_and_flush_observes_it(test_db):
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    async with uow.UOW(store) as repo:
        first = await repo.get_for_update(Doc, UID)
        second = await repo.get_for_update(Doc, UID)

        assert first is second

        first.value = 5

        assert second.value == 5

    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 1, "value": 5}


async def test_read_without_update_leaves_document_untouched(test_db):
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    async with uow.UOW(store) as repo:
        doc = await repo.get(Doc, UID)
        again = await repo.get(Doc, UID)

        assert doc is again

        doc.value = 5

    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 0, "value": 1}


async def test_clean_body_flushes_every_dirty_document(test_db):
    other_uid = domain.UID("other")
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    await test_db[COLLECTION].insert_one({"_id": other_uid, "ver": 0, "value": 2})
    store = mongo.Store(test_db)

    async with uow.UOW(store) as repo:
        first = await repo.get_for_update(Doc, UID)
        second = await repo.get_for_update(Doc, other_uid)
        first.value = 10
        second.value = 20

    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 1, "value": 10}
    assert await test_db[COLLECTION].find_one({"_id": other_uid}) == {"_id": other_uid, "ver": 1, "value": 20}


async def test_body_exception_flushes_nothing(test_db):
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    async def _mutate_and_fail() -> None:
        async with uow.UOW(store) as repo:
            doc = await repo.get_for_update(Doc, UID)
            doc.value = 10
            raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await _mutate_and_fail()

    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 0, "value": 1}


async def test_get_creates_missing_singleton_at_version_zero(test_db):
    store = mongo.Store(test_db)

    async with uow.UOW(store) as repo:
        doc = await repo.get(Doc)

    assert doc.uid == domain.UID(Doc.__name__)
    assert doc.value == 0
    assert await test_db[COLLECTION].find_one({"_id": doc.uid}) == {"_id": doc.uid, "ver": 0}


async def test_delete_is_immediate_and_outside_the_flush(test_db):
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    async def _delete_and_fail() -> None:
        async with uow.UOW(store) as repo:
            doc = await repo.get_for_update(Doc, UID)
            await repo.delete(doc)

            assert await test_db[COLLECTION].find_one({"_id": UID}) is None

            raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await _delete_and_fail()

    assert await test_db[COLLECTION].find_one({"_id": UID}) is None


async def test_version_conflict_surfaces_and_a_fresh_retry_succeeds(test_db):
    await test_db[COLLECTION].insert_one({"_id": UID, "ver": 0, "value": 1})
    store = mongo.Store(test_db)

    async def _stale_flush() -> None:
        async with uow.UOW(store) as stale_repo:
            stale_doc = await stale_repo.get_for_update(Doc, UID)

            async with uow.UOW(store) as repo:
                doc = await repo.get_for_update(Doc, UID)
                doc.value = 1

            assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 1, "value": 1}

            stale_doc.value = 2

    with pytest.raises(ExceptionGroup) as err:
        await _stale_flush()

    conflict = errors.get_root_poptimizer_error(err.value)
    assert isinstance(conflict, errors.POError)
    assert "wrong version" in str(conflict)

    async with uow.UOW(store) as repo:
        doc = await repo.get_for_update(Doc, UID)
        doc.value = 3

    assert await test_db[COLLECTION].find_one({"_id": UID}) == {"_id": UID, "ver": 2, "value": 3}


async def test_uow_is_single_use(test_db):
    store = mongo.Store(test_db)
    one = uow.UOW(store)

    async with one as repo:
        await repo.get(Doc, UID)

    async def _reenter() -> None:
        async with one:
            raise AssertionError("second enter must not succeed")

    with pytest.raises(errors.ControllersError, match="already entered"):
        await _reenter()
