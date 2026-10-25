"""External storage is replaced at the Firestore boundary; real routes/models run."""
import copy
from datetime import datetime, timezone
import itertools
import threading

import pytest


class Snapshot:
    def __init__(self, ref):
        self.id = ref.id
        self.reference = ref
        self._data = copy.deepcopy(ref.store.get(ref.path))
        self.exists = self._data is not None

    def to_dict(self):
        return copy.deepcopy(self._data)


class Document:
    def __init__(self, db, collection, id):
        self.db, self.store, self.id = db, db.store, id
        self.path = (collection, id)

    def get(self, transaction=None, **kwargs):
        return Snapshot(self)

    def set(self, data, **kwargs):
        self.store[self.path] = copy.deepcopy(data)

    def create(self, data, **kwargs):
        assert self.path not in self.store
        self.set(data)

    def update(self, data, **kwargs):
        self.store[self.path].update(copy.deepcopy(data))

    def delete(self, **kwargs):
        self.store.pop(self.path, None)


class Query:
    def __init__(self, db, name, filters=(), ordering=None, cap=None):
        self.db, self.name, self.filters, self.ordering, self.cap = db, name, filters, ordering, cap

    def document(self, id=None):
        return Document(self.db, self.name, id or f'test-{next(self.db.ids)}')

    def where(self, *, filter):
        return Query(self.db, self.name, (*self.filters,filter),self.ordering,self.cap)

    def order_by(self, name, direction='ASCENDING'):
        return Query(self.db,self.name,self.filters,(name,direction),self.cap)

    def limit(self, cap):
        return Query(self.db,self.name,self.filters,self.ordering,cap)

    def stream(self, **kwargs):
        docs = [self.document(id).get() for name,id in list(self.db.store) if name == self.name]
        for f in self.filters:
            if f.op_string == '>=': docs = [d for d in docs if d.to_dict()[f.field_path] >= f.value]
            elif f.op_string == '<=': docs = [d for d in docs if d.to_dict()[f.field_path] <= f.value]
        if self.ordering:
            field,direction = self.ordering
            docs.sort(key=lambda d:(d.to_dict().get(field,''),d.id),reverse=direction=='DESCENDING')
        return iter(docs[:self.cap])


class MemoryDB:
    def __init__(self):
        self.store = {}
        self.ids = itertools.count(1)
        self.lock = threading.RLock()

    def collection(self, name):
        return Query(self, name)

    def transaction(self):
        return MemoryTransaction(self)


class MemoryTransaction:
    _read_only = False
    _max_attempts = 1

    def __init__(self, db):
        self.db, self._id, self.writes = db, None, []
        self.locked = False

    def _clean_up(self):
        self.writes=[]

    def _begin(self, retry_id=None):
        self.db.lock.acquire()
        self.locked=True
        self._id=b'test-transaction'

    def set(self, ref, data):
        self.writes.append((ref,copy.deepcopy(data)))

    def _commit(self):
        for ref,data in self.writes: ref.set(data)
        self._rollback()

    def _rollback(self):
        if self.locked:
            self.locked=False
            self.db.lock.release()


@pytest.fixture
def db(monkeypatch):
    import database
    fake = MemoryDB()
    monkeypatch.setattr(database, 'init_firebase', lambda:fake)
    monkeypatch.setattr(database, '_db', fake)
    from services import ai_chat
    monkeypatch.setattr(ai_chat, 'limiter', ai_chat.RateLimiter())
    return fake


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c

