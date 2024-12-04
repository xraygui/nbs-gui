from qtpy.QtCore import QObject, Signal, QThread
from qtpy.QtCore import QAbstractTableModel, Qt
import orjson


class RedisWatcherThread(QThread):
    change_detected = Signal(str, str)  # key, event

    def __init__(self, redis_client, prefix, topic):
        super().__init__()
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        self.prefix = f"{prefix}{topic}"
        # Get db number directly from redis client
        self.db = redis_client.connection_pool.connection_kwargs["db"]
        self._running = True

    def run(self):
        # Enable keyspace notifications
        self.redis.config_set("notify-keyspace-events", "KEA")
        # Subscribe to pattern with prefix, using correct db number
        self.pubsub.psubscribe(f"__keyspace@{self.db}__:{self.prefix}*")

        while self._running:
            message = self.pubsub.get_message()
            if message and message["type"] == "pmessage":
                # Extract key from channel, accounting for db number
                key = message["channel"].decode().split(f"@{self.db}__:")[1]
                event = message["data"].decode()
                if key.startswith(self.prefix):
                    self.change_detected.emit(key, event)
            self.msleep(10)  # Small delay to prevent CPU hogging

    def stop(self):
        self._running = False
        self.pubsub.unsubscribe()
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

    changed = Signal()  # Emitted when any value changes
    key_changed = Signal(str)  # Emitted with the specific key that changed

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
        import redis

        redis_client = redis.Redis(
            host=settings["host"],
            port=settings.get("port", 6379),
            db=settings.get("db", 0),
        )
        prefix = settings.get("prefix", "")
        return cls(redis_client, prefix, topic, parent)

    def __init__(self, redis_client, prefix, topic="", parent=None):
        # print("Initializing QtRedisJSONDict")
        super().__init__()
        # print("After QtRJD super init")
        self._redis = redis_client
        self._prefix = f"{prefix}{topic}"
        # print(f"Redis dict with {self._prefix}")
        self._cache = {}  # Local cache
        self._watcher = RedisWatcherThread(redis_client, prefix, topic)
        self._watcher.change_detected.connect(self._on_redis_change)
        self._watcher.start()
        # Initial load of cache
        self._refresh_cache()

    def _refresh_cache(self):
        """Load all data from Redis into the cache"""
        keys = self._redis.keys(f"{self._prefix}*")
        # print(f"Refresh, get {keys}")
        pipe = self._redis.pipeline()
        for key in keys:
            pipe.get(key)
        values = pipe.execute()

        self._cache.clear()
        for key, value in zip(keys, values):
            if value is not None:
                stripped_key = key.decode()[len(self._prefix) :]
                try:
                    self._cache[stripped_key] = orjson.loads(value)
                except Exception:
                    # If we can't decode the JSON, skip this key
                    continue

    def _on_redis_change(self, key, event):
        """Handle Redis key change events"""
        stripped_key = key[len(self._prefix) :]

        if event in ["set", "hset"]:
            # Update cache from Redis
            value = self._redis.get(key)
            if value is not None:
                try:
                    self._cache[stripped_key] = orjson.loads(value)
                except Exception:
                    # If we can't decode the JSON, remove from cache
                    self._cache.pop(stripped_key, None)
        elif event in ["del", "hdel", "expired"]:
            # Remove from cache
            self._cache.pop(stripped_key, None)

        self.key_changed.emit(stripped_key)
        self.changed.emit()

    def __getitem__(self, key):
        return self._cache[key]

    def __setitem__(self, key, value):
        # Update Redis
        json_data = orjson.dumps(value)
        self._redis.set(f"{self._prefix}{key}", json_data)
        # Update cache immediately
        self._cache[key] = value

    def __delitem__(self, key):
        # Delete from Redis
        self._redis.delete(f"{self._prefix}{key}")
        # Delete from cache immediately
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
        # Clear Redis
        keys = self._redis.keys(f"{self._prefix}*")
        if keys:
            self._redis.delete(*keys)
        # Clear cache
        self._cache.clear()

    def update(self, other):
        # Update Redis in a pipeline
        pipe = self._redis.pipeline()
        for key, value in other.items():
            json_data = orjson.dumps(value)
            pipe.set(f"{self._prefix}{key}", json_data)
        pipe.execute()
        # Update cache
        self._cache.update(other)

    def cleanup(self):
        """Stop the watcher thread when done"""
        self._watcher.stop()

    def refresh(self):
        """Force a refresh of the cache from Redis"""
        self._refresh_cache()
        self.changed.emit()


class NestedRedisTableModel(QAbstractTableModel):
    def __init__(self, redis_dict, parent=None):
        """
        Parameters
        ----------
        redis_dict : QtRedisJSONDict
            The Redis dictionary to model
        parent : QObject, optional
            Parent Qt object
        """
        super().__init__(parent)
        # print("Initializing NestedREDISTableModel")
        self._data = redis_dict
        # print("Initialized data")
        self._data.changed.connect(self.update)
        self.update()

    def data(self, index, role):
        if role == Qt.DisplayRole:
            key = list(self._data.keys())[index.row()]
            key2 = list(self._data[key].keys())[index.column()]
            return str(self._data[key][key2])

    def rowCount(self, index):
        return len(self._data.keys())

    def columnCount(self, index):
        mincol = None
        for k, v in self._data.items():
            if mincol is None:
                mincol = len(v.keys())
            else:
                mincol = min(len(v.keys()), mincol)
        if mincol is None:
            return 0
        else:
            return mincol

    def update(self):
        self.beginResetModel()
        self._rows = list(self._data.keys())
        if len(self._rows) > 0:
            for k, v in self._data.items():
                self._columns = list(v.keys())
                break
        self.endResetModel()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._columns[section])
            if orientation == Qt.Vertical:
                return self._rows[section]

    def cleanup(self):
        """Cleanup is now optional since we don't own the redis dict"""
        pass
