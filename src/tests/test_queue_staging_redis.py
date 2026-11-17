"""Tests for the staging queue kept in the beamline Redis."""

from types import SimpleNamespace

import fakeredis
import orjson
import pytest

from nbs_gui.models.QtReQueueStaging import QueueStagingModel
from nbs_gui.models.stagingStore import (
    RedisStagingStore,
    StagingConflict,
    make_staging_store,
)

PREFIX = "test-"
KEY = f"{PREFIX}staging:queue"


def plan(name, **kwargs):
    return {"item_type": "plan", "name": name, "args": [], "kwargs": kwargs}


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


@pytest.fixture
def run_engine():
    return SimpleNamespace(_allowed_plans={})


def make_model(run_engine, redis_client, author="nbs-gui:a:alice"):
    store = RedisStagingStore(redis_client, PREFIX, author=author)
    return QueueStagingModel(run_engine, store=store)


def stored(redis_client):
    return orjson.loads(redis_client.get(KEY))


def names(model):
    return [item["name"] for item in model.staged_plans]


def test_local_without_redis(qapp, run_engine):
    model = QueueStagingModel(run_engine, store_note="no beamline Redis settings")
    text, warning = model.store_status
    assert warning and "local" in text and "no beamline Redis settings" in text
    model.add_plan(plan("count"))
    assert names(model) == ["count"]


def test_add_writes_redis(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    assert model.store_status == (model.store.description, False)
    model.add_plan(plan("count", num=3))
    data = stored(redis_client)
    assert data["version"] == 1
    assert data["updated_by"] == "nbs-gui:a:alice"
    assert [i["name"] for i in data["items"]] == ["count"]
    assert data["items"][0]["item_uid"] == model.staged_plans[0]["item_uid"]


def test_second_gui_sees_queue(qapp, run_engine, redis_client):
    first = make_model(run_engine, redis_client)
    first.queue_item_add_batch(items=[plan("a"), plan("b")])
    second = make_model(run_engine, redis_client, author="nbs-gui:b:bob")
    assert names(second) == ["a", "b"]


def test_one_write_per_action(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    model.queue_item_add_batch(items=[plan("a"), plan("b"), plan("c")])
    assert stored(redis_client)["version"] == 1
    model.set_selection([2])
    model.queue_items_move_to_top()
    assert stored(redis_client)["version"] == 2
    assert [i["name"] for i in stored(redis_client)["items"]] == ["c", "a", "b"]
    model.clear_all()
    assert stored(redis_client) | {"updated": 0} == {
        "version": 3, "items": [], "updated": 0, "updated_by": "nbs-gui:a:alice"
    }


def test_selection_is_local(qapp, run_engine, redis_client):
    first = make_model(run_engine, redis_client)
    first.queue_item_add_batch(items=[plan("a"), plan("b")])
    second = make_model(run_engine, redis_client)
    first.set_selection([0])
    assert second.selected_plan_indices == []
    assert stored(redis_client)["version"] == 1


def test_conflict_reapplies_change(qapp, run_engine, redis_client):
    first = make_model(run_engine, redis_client)
    first.queue_item_add_batch(items=[plan("a"), plan("b")])
    second = make_model(run_engine, redis_client)
    second.add_plan(plan("c"))
    # first has not reloaded: its removal is based on version 1
    first.remove_plans([0])
    assert names(first) == ["b", "c"]
    assert stored(redis_client)["version"] == 3
    assert [i["name"] for i in stored(redis_client)["items"]] == ["b", "c"]


def test_repeated_conflict_keeps_stored_queue(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    model.add_plan(plan("a"))
    other = RedisStagingStore(redis_client, PREFIX)

    def save(items, base_version):
        other.save([plan("theirs") | {"item_uid": "x"}], other.load()[0])
        raise StagingConflict("changed")

    model.store.save = save
    model.add_plan(plan("mine"))
    assert names(model) == ["theirs"]
    text, warning = model.store_status
    assert warning and "not applied" in text


def test_remote_change_reloads(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    model.add_plan(plan("a"))
    seen = []
    model.events.plan_queue_changed.connect(lambda event: seen.append(event))
    other = RedisStagingStore(redis_client, PREFIX)
    other.save(model.staged_plans + [plan("b") | {"item_uid": "u-b"}], 1)
    model.on_redis_key_changed(KEY, "set")
    assert names(model) == ["a", "b"]
    assert len(seen) == 1
    # our own write does not trigger a second reload
    model.on_redis_key_changed(KEY, "set")
    assert len(seen) == 1


def test_proposals_are_ignored(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    model.add_plan(plan("a"))
    proposal = {"id": "abc", "base_version": 1, "status": "pending",
                "ops": [{"op": "add", "item": plan("p"), "after_uid": None}]}
    redis_client.set(f"{PREFIX}staging:proposal:abc", orjson.dumps(proposal))
    model.on_redis_key_changed(f"{PREFIX}staging:proposal:abc", "set")
    assert names(model) == ["a"]
    assert names(make_model(run_engine, redis_client)) == ["a"]


def test_deleted_key_empties_queue(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)
    model.add_plan(plan("a"))
    redis_client.delete(KEY)
    model.on_redis_key_changed(KEY, "del")
    assert names(model) == []
    model.add_plan(plan("b"))
    assert stored(redis_client)["version"] == 1


def test_save_failure_keeps_local_change(qapp, run_engine, redis_client):
    model = make_model(run_engine, redis_client)

    def save(items, base_version):
        raise ConnectionError("down")

    model.store.save = save
    model.add_plan(plan("a"))
    assert names(model) == ["a"]
    text, warning = model.store_status
    assert warning and "only in this GUI" in text


def test_store_rejects_stale_version(redis_client):
    store = RedisStagingStore(redis_client, PREFIX)
    assert store.load() == (0, [])
    assert store.save([plan("a")], 0) == 1
    with pytest.raises(StagingConflict):
        store.save([plan("b")], 0)
    assert store.load()[1] == [plan("a")]


def test_make_staging_store(redis_client):
    store, note = make_staging_store(None)
    assert store is None and "no beamline Redis" in note

    status = SimpleNamespace(_redis_client=redis_client, _redis_prefix=PREFIX)
    store, note = make_staging_store(status)
    assert store.key == KEY and note == ""

    class Down:
        def ping(self):
            raise ConnectionError("refused")

    store, note = make_staging_store(SimpleNamespace(_redis_client=Down()))
    assert store is None and "unreachable" in note
