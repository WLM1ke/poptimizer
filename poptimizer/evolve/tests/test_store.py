import math
from types import SimpleNamespace

import bson
import pymongo
import pytest

from poptimizer.evolve import store


@pytest.fixture(scope="module", autouse=True)
def set_test_collection():
    # noinspection PyProtectedMember
    saved_collection = store._COLLECTION
    test_collection = saved_collection.database["test"]
    store._COLLECTION = test_collection

    yield

    store._COLLECTION = saved_collection
    test_collection.drop()


def test_get_collection():
    collection = store.get_collection()
    assert isinstance(collection, pymongo.collection.Collection)
    assert collection.name == "test"


@pytest.fixture(scope="class", name="field_instance")
def make_field_and_instance():
    field = store.BaseField()
    instance = SimpleNamespace()
    instance._update = {}
    return field, instance


class TestBaseField:
    def test_set_name_index(self):
        field = store.BaseField(index=True)
        field.__set_name__(SimpleNamespace, "some")

        assert field._name == store.ID

    def test_set_name(self, field_instance):
        field, _ = field_instance
        field.__set_name__(SimpleNamespace, "some")

        assert field._name == "some"

    def test_get_raise(self, field_instance):
        field, instance = field_instance

        with pytest.raises(AttributeError) as error:
            field.__get__(instance, SimpleNamespace)

        assert "'SimpleNamespace' object has no attribute 'some'" in str(error.value)

    def test_set(self, field_instance):
        field, instance = field_instance
        field.__set__(instance, 42)

        assert hasattr(instance, "some")
        assert instance.some == 42
        assert len(instance._update) == 1
        assert instance._update["some"] == 42

    def test_get(self, field_instance):
        field, instance = field_instance

        assert field.__get__(instance, SimpleNamespace) == 42


@pytest.fixture(scope="class", name="default_field_instance")
def make_default_field_and_instance():
    field = store.DefaultField(53)
    field.__set_name__(SimpleNamespace, "some")
    instance = SimpleNamespace()
    instance._update = {}
    return field, instance


class TestDefaultField:
    def test_unset_get(self, default_field_instance):
        field, instance = default_field_instance

        assert field.__get__(instance, SimpleNamespace) == 53

    def test_set_get(self, default_field_instance):
        field, instance = default_field_instance
        field.__set__(instance, 64)

        assert field.__get__(instance, SimpleNamespace) == 64


@pytest.fixture(scope="class", name="genotype_field_instance")
def make_genotype_field_and_instance():
    field = store.GenotypeField()
    field.__set_name__(SimpleNamespace, "some")
    instance = SimpleNamespace()
    instance._update = {}
    return field, instance


class TestGenotypeField:
    def test_set_not_genotype(self, genotype_field_instance):
        field, instance = genotype_field_instance
        field.__set__(instance, None)
        rez = field.__get__(instance, SimpleNamespace)

        assert isinstance(rez, store.Genotype)
        assert isinstance(instance.some, store.Genotype)
        assert rez is instance.some

    def test_set_genotype(self, genotype_field_instance):
        field, instance = genotype_field_instance
        genotype = store.Genotype(None)
        field.__set__(instance, genotype)

        assert genotype is field.__get__(instance, SimpleNamespace)
        assert genotype is instance.some


class TestDoc:
    def test_new_doc_and_save(self):
        assert store.get_collection().count_documents({}) == 0

        genotype = store.Genotype()
        doc = store.Doc(genotype=genotype)

        assert store.get_collection().count_documents({}) == 0
        assert len(doc._update) == 2
        assert isinstance(doc.id, bson.ObjectId)
        assert doc.genotype is genotype
        assert doc.wins == 0
        assert doc.model is None

        assert doc.llh == -math.inf
        assert doc.ir == -math.inf

        assert doc.date is None
        assert doc.timer == 0
        assert doc.tickers is None

        doc.save()

        assert store.get_collection().count_documents({}) == 1
        assert len(doc._update) == 0

    def test_load_wrong_doc(self):
        id_ = bson.ObjectId()
        with pytest.raises(store.IdError) as error:
            store.Doc(id_=id_)
        assert str(id_) in str(error.value)

    def test_load_doc(self):
        db_doc = store.get_collection().find_one()
        doc = store.Doc(id_=db_doc[store.ID])

        assert len(doc._update) == 0
        assert doc.id == db_doc[store.ID]
        assert doc.genotype == db_doc["genotype"]
        assert doc.wins == 0
        assert doc.model is None

        assert doc.llh == -math.inf

        assert doc.date is None
        assert doc.timer == 0
        assert doc.tickers is None

    def test_load_doc_update_and_save(self):
        db_doc = store.get_collection().find_one()
        doc = store.Doc(id_=db_doc[store.ID])

        assert len(doc._update) == 0

        doc.wins = 42
        doc.llh = 2.2
        doc.timer = 111

        assert len(doc._update) == 3

        doc.save()

        assert len(doc._update) == 0

        doc_loaded = store.Doc(id_=db_doc[store.ID])

        assert len(doc_loaded._update) == 0
        assert doc_loaded.id == db_doc[store.ID]
        assert doc_loaded.genotype == db_doc["genotype"]
        assert doc_loaded.wins == 42
        assert doc_loaded.model is None
        assert doc_loaded.llh == 2.2
        assert doc_loaded.date is None
        assert doc_loaded.timer == 111
        assert doc_loaded.tickers is None

    def test_delete(self):
        assert store.get_collection().count_documents({}) == 1

        db_doc = store.get_collection().find_one()
        doc = store.Doc(id_=db_doc[store.ID])

        doc.delete()

        assert store.get_collection().count_documents({}) == 0
