from qtpy.QtCore import QObject, Signal, QThread
from qtpy.QtCore import QAbstractTableModel, Qt
import orjson
import redis
from nbs_bl.redisUtils import open_redis_client_from_settings


class RedisWatcherThread(QThread):
    """
    Thread that watches for Redis keyspace notifications and emits signals on changes.

    Parameters
    ----------
    redis_client : redis.Redis
        Redis client instance
    prefix : str
        Prefix to watch for changes (watches prefix*)
    """

    _watchers = {}
    change_detected = Signal(str, str)

    @classmethod
    def get_or_create(cls, redis_client, prefix):
        """
        Get an existing watcher or create a new one for this Redis server and prefix.

        Parameters
        ----------
        redis_client : redis.Redis
            Redis client instance
        prefix : str
            Prefix to watch for changes

        Returns
        -------
        RedisWatcherThread
            Shared watcher instance for this server/prefix combination
        """
        conn_kwargs = redis_client.connection_pool.connection_kwargs
        cache_key = (
            conn_kwargs.get("host", "localhost"),
            conn_kwargs.get("port", 6379),
            conn_kwargs.get("db", 0),
            prefix,
        )
        if cache_key not in cls._watchers:
            watcher = cls(redis_client, prefix)
            watcher.start()
            cls._watchers[cache_key] = watcher
        return cls._watchers[cache_key]

    def __init__(self, redis_client, prefix):
        super().__init__()
        self._redis = redis_client
        self._pubsub = None
        self._prefix = prefix
        self._db = redis_client.connection_pool.connection_kwargs.get("db", 0)
        self._running = True

    def run(self):
        try:
            self._redis.config_set("notify-keyspace-events", "KEA")
        except redis.exceptions.ResponseError:
            pass
        self._pubsub = self._redis.pubsub()
        self._pubsub.psubscribe(f"__keyspace@{self._db}__:{self._prefix}*")

        while self._running:
            message = self._pubsub.get_message(timeout=1.0)
            if message and message["type"] == "pmessage":
                key = message["channel"].decode().split(f"@{self._db}__:")[1]
                event = message["data"].decode()
                if key.startswith(self._prefix):
                    self.change_detected.emit(key, event)

    def stop(self):
        self._running = False
        if self._pubsub is not None:
            self._pubsub.unsubscribe()
        self.wait()


class QtRedisJSONDict(QObject):
    """
    A Qt-friendly wrapper around RedisJSONDict that maintains a local cache
    and emits signals on changes.

    Parameters
    ----------
    redis_client : redis.Redis
        Redis client instance
    prefix : str
        Global prefix for all Redis keys
    topic : str, optional
        Additional topic-specific prefix
    parent : QObject, optional
        Parent Qt object
    """

    changed = Signal()
    key_changed = Signal(str)

    @classmethod
    def from_settings(cls, settings, topic="", parent=None):
        """
        Create a QtRedisJSONDict instance from settings dictionary.

        Parameters
        ----------
        settings : dict
            Dictionary containing Redis settings with keys:
            - host: Redis host
            - port: Redis port (optional)
            - db: Redis database number (optional)
            - prefix: Global prefix for keys (optional)
        topic : str, optional
            Additional topic-specific prefix
        parent : QObject, optional
            Parent Qt object

        Returns
        -------
        QtRedisJSONDict
            New instance configured with the given settings
        """

        redis_client = open_redis_client_from_settings(settings)

        prefix = settings.get("prefix", "")
        return cls(redis_client, prefix, topic, parent)

    def __init__(self, redis_client, prefix, topic="", parent=None):
        super().__init__(parent)
        self._redis = redis_client
        self._prefix = prefix
        self._topic = topic
        self._redis_key = f"{prefix}{topic}"
        self._cache = {}
        try:
            self._refresh_cache()
        except Exception as e:
            print(f"Error {e} for Redis client: {self._redis.connection_pool.connection_kwargs}")
            raise
        self._watcher = RedisWatcherThread.get_or_create(redis_client, prefix)
        self._watcher.change_detected.connect(self._on_redis_change)

    def _refresh_cache(self):
        """Load all data from Redis into the cache."""
        keys = self._redis.keys(f"{self._redis_key}*")
        pipe = self._redis.pipeline()
        for key in keys:
            pipe.get(key)
        values = pipe.execute()

        self._cache.clear()
        for key, value in zip(keys, values):
            if value is not None:
                stripped_key = key.decode()[len(self._redis_key) :]
                try:
                    self._cache[stripped_key] = orjson.loads(value)
                except Exception:
                    continue

    def _on_redis_change(self, key, event):
        """Handle Redis key change events."""
        if not key.startswith(self._redis_key):
            return

        stripped_key = key[len(self._redis_key) :]

        if event in ["set", "hset"]:
            value = self._redis.get(key)
            if value is not None:
                try:
                    self._cache[stripped_key] = orjson.loads(value)
                except Exception:
                    self._cache.pop(stripped_key, None)
        elif event in ["del", "hdel", "expired"]:
            self._cache.pop(stripped_key, None)

        self.key_changed.emit(stripped_key)
        self.changed.emit()

    def __getitem__(self, key):
        return self._cache[key]

    def __setitem__(self, key, value):
        json_data = orjson.dumps(value)
        self._redis.set(f"{self._redis_key}{key}", json_data)
        self._cache[key] = value

    def __delitem__(self, key):
        self._redis.delete(f"{self._redis_key}{key}")
        del self._cache[key]

    def __iter__(self):
        return iter(self._cache)

    def __len__(self):
        return len(self._cache)

    def items(self):
        return self._cache.items()

    def keys(self):
        return self._cache.keys()

    def values(self):
        return self._cache.values()

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def clear(self):
        keys = self._redis.keys(f"{self._redis_key}*")
        if keys:
            self._redis.delete(*keys)
        self._cache.clear()

    def update(self, other):
        pipe = self._redis.pipeline()
        for key, value in other.items():
            json_data = orjson.dumps(value)
            pipe.set(f"{self._redis_key}{key}", json_data)
        pipe.execute()
        self._cache.update(other)

    def cleanup(self):
        """Disconnect from the shared watcher thread."""
        try:
            self._watcher.change_detected.disconnect(self._on_redis_change)
        except (TypeError, RuntimeError):
            pass

    def refresh(self):
        """Force a refresh of the cache from Redis."""
        self._refresh_cache()
        self.changed.emit()


class NestedRedisTableModel(QAbstractTableModel):
    """
    A table model for displaying nested Redis dictionary data.

    Parameters
    ----------
    redis_dict : QtRedisJSONDict
        The Redis dictionary to model
    parent : QObject, optional
        Parent Qt object
    """

    def __init__(self, redis_dict, parent=None):
        super().__init__(parent)
        self._data = redis_dict
        self._rows = []
        self._columns = []
        self._data.changed.connect(self.update)
        self.update()

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.row() < len(self._rows) and index.column() < len(self._columns):
                key = self._rows[index.row()]
                key2 = self._columns[index.column()]
                return str(self._data[key].get(key2, ""))
        return None

    def rowCount(self, index=None):
        return len(self._rows)

    def columnCount(self, index=None):
        return len(self._columns)

    def update(self):
        self.beginResetModel()
        self._rows = list(self._data.keys())
        self._columns = []
        if len(self._rows) > 0:
            min_cols = None
            for k, v in self._data.items():
                if min_cols is None:
                    min_cols = set(v.keys())
                else:
                    min_cols &= set(v.keys())
            if min_cols:
                first_key = self._rows[0]
                self._columns = [k for k in self._data[first_key].keys() if k in min_cols]
        self.endResetModel()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal and section < len(self._columns):
                return str(self._columns[section])
            if orientation == Qt.Vertical and section < len(self._rows):
                return self._rows[section]
        return None

    def cleanup(self):
        """Cleanup is now optional since we don't own the redis dict."""
        pass
