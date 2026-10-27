from bson import ObjectId
import pytest

from chromaforge.database import Store


class CollectionSpy:
    def __init__(self):
        self.filter = None

    def update_one(self, query, update):
        self.filter = query
        self.update = update
        return type("Result", (), {"matched_count": 1})()

    def delete_one(self, query):
        self.filter = query
        return type("Result", (), {"deleted_count": 1})()


def test_updates_and_deletes_require_ownership():
    collection = CollectionSpy()
    store = Store.__new__(Store)
    store.db = {"saved_colors": collection}
    owner, item = ObjectId(), ObjectId()
    store.update("saved_colors", owner, item, {"name": "New", "user_id": ObjectId()})
    assert collection.filter == {"_id": item, "user_id": owner}
    assert "user_id" not in collection.update["$set"]
    store.delete("saved_colors", owner, item)
    assert collection.filter == {"_id": item, "user_id": owner}


def test_registration_rejects_invalid_input_before_db_write():
    store = Store.__new__(Store)
    with pytest.raises(ValueError):
        store.register("A", "x", "bad", "short")
