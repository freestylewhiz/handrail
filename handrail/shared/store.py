"""Atomic documents, append-only journal, and durable delivery intents.

Read methods use SQLite mode=ro and never create files. Network/process calls
must not run inside a transaction. The journal and aggregate update commit as
one unit; outbox delivery is an explicit later operation.
"""
import json
import os
import sqlite3
import fcntl
import threading
from contextlib import contextmanager
from pathlib import Path

from .errors import HandrailError
from .identity import now, new_id, digest

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (version INTEGER NOT NULL);
INSERT INTO meta SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM meta);
CREATE TABLE IF NOT EXISTS documents (
 kind TEXT NOT NULL, id TEXT NOT NULL, value TEXT NOT NULL,
 PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 entity TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (
 key TEXT PRIMARY KEY, topic TEXT NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL, at TEXT NOT NULL, result TEXT);
"""


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Transaction:
    def __init__(self, connection):
        self.connection = connection

    def get(self, kind, identity):
        row = self.connection.execute("SELECT value FROM documents WHERE kind=? AND id=?",
                                      (kind, str(identity))).fetchone()
        return json.loads(row[0]) if row else None

    def require(self, kind, identity):
        value = self.get(kind, identity)
        if value is None:
            raise HandrailError("NOT_FOUND", f"Unknown {kind}: {identity}")
        return value

    def list(self, kind):
        return [json.loads(row[0]) for row in self.connection.execute(
            "SELECT value FROM documents WHERE kind=? ORDER BY id", (kind,))]

    def put(self, kind, identity, value):
        self.connection.execute("INSERT INTO documents VALUES(?,?,?) ON CONFLICT(kind,id) "
                                "DO UPDATE SET value=excluded.value", (kind, str(identity), encode(value)))

    def event(self, entity, kind, data):
        identity = new_id("event-")
        self.connection.execute("INSERT INTO events(id,entity,kind,at,data) VALUES(?,?,?,?,?)",
                                (identity, str(entity), kind, now(), encode(data)))
        return identity

    def enqueue(self, topic, key, payload):
        encoded = encode(payload)
        old = self.connection.execute("SELECT topic,payload FROM outbox WHERE key=?", (key,)).fetchone()
        if old:
            if tuple(old) != (topic, encoded):
                raise HandrailError("OPERATION_CONFLICT", "Outbox key already has a different payload")
            return key
        self.connection.execute("INSERT INTO outbox VALUES(?,?,?,?,?,NULL)",
                                (key, topic, encoded, "pending", now()))
        return key

    def delivery(self, key, status, result=None):
        if status not in ("pending", "sending", "unknown", "complete", "failed"):
            raise HandrailError("INVALID_STATE", "Invalid delivery state")
        self.connection.execute("UPDATE outbox SET status=?,result=? WHERE key=?",
                                (status, encode(result), key))

    def intent(self, identity, action, request):
        """Return an existing intent only when its original request is identical."""
        old = self.get("operation", identity)
        fingerprint = digest({"action": action, "request": request})
        if old:
            if old["fingerprint"] != fingerprint:
                raise HandrailError("OPERATION_CONFLICT", "Operation ID belongs to a different request")
            return old
        record = {"id": identity, "action": action, "request": request,
                  "fingerprint": fingerprint, "status": "prepared", "created_at": now()}
        self.put("operation", identity, record)
        return record


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self._held_locks = set()
        self._thread_lock = threading.RLock()

    @contextmanager
    def exclusive(self, name):
        """Serialize external effects as well as the short database transactions."""
        with self._thread_lock:
            with self._exclusive_process(name):
                yield

    @contextmanager
    def _exclusive_process(self, name):
        if name in self._held_locks:
            yield
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.path.parent / (digest(name) + ".lock")
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise HandrailError("OPERATION_BUSY", "Another coordinator is changing this resource", retryable=True) from None
            self._held_locks.add(name)
            try:
                yield
            finally:
                self._held_locks.remove(name)
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    def _connect(self, write=False):
        if self.path.is_symlink():
            raise HandrailError("STATE_PATH_INVALID", "State database must not be a symlink")
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # A private directory also protects SQLite's rollback journal.
            os.chmod(self.path.parent, 0o700)
            descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
            os.close(descriptor)
            os.chmod(self.path, 0o600)
            connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
            connection.executescript(SCHEMA)
        elif self.path.exists():
            connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True,
                                         timeout=10, isolation_level=None)
        else:
            return None
        version = connection.execute("SELECT version FROM meta").fetchone()
        if not version or version[0] != 1:
            connection.close()
            raise HandrailError("STATE_VERSION", "Unsupported state schema; preserve the existing database")
        return connection

    @contextmanager
    def transaction(self):
        connection = self._connect(write=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield Transaction(connection)
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def _read(self, function, default):
        connection = self._connect()
        if connection is None:
            return default
        try:
            return function(connection)
        finally:
            connection.close()

    def read(self, kind, identity):
        return self._read(lambda conn: Transaction(conn).get(kind, identity), None)

    def list(self, kind):
        return self._read(lambda conn: Transaction(conn).list(kind), [])

    def history(self, entity=None):
        def read(conn):
            query = "SELECT sequence,id,entity,kind,at,data FROM events"
            rows = conn.execute(query + (" WHERE entity=?" if entity else "") + " ORDER BY sequence",
                                (entity,) if entity else ())
            return [{"sequence": r[0], "id": r[1], "entity": r[2], "kind": r[3], "at": r[4],
                     "data": json.loads(r[5])} for r in rows]
        return self._read(read, [])

    def outbox(self, topic=None):
        def read(conn):
            rows = conn.execute("SELECT key,topic,payload,status,at,result FROM outbox" +
                                (" WHERE topic=?" if topic else "") + " ORDER BY rowid",
                                (topic,) if topic else ())
            return [{"key": r[0], "topic": r[1], "payload": json.loads(r[2]), "status": r[3],
                     "at": r[4], "result": json.loads(r[5]) if r[5] else None} for r in rows]
        return self._read(read, [])
