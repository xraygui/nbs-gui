"""Shared storage for the staging queue in the beamline Redis."""

import copy
import getpass
import socket
import time

import orjson

STAGING_QUEUE_TOPIC = "staging:queue"


class StagingConflict(Exception):
    """The stored staging queue changed since the version a write was based on."""


def staging_author():
    """
    Name recorded as ``updated_by`` on writes from this GUI.

    Returns
    -------
    str
        ``"nbs-gui:<host>:<login>"``.
    """
    try:
        login = getpass.getuser()
    except Exception:
        login = "unknown"
    return f"nbs-gui:{socket.gethostname()}:{login}"


class RedisStagingStore:
    """
    The staging queue kept in one beamline Redis key.

    The key ``{prefix}staging:queue`` holds JSON
    ``{"version", "items", "updated", "updated_by"}``. A missing key is an
    empty queue at version 0. Every write checks that the stored version is
    the one the change was based on, so concurrent writers never overwrite
    each other.

    Parameters
    ----------
    redis_client : redis.Redis
        Client for the beamline Redis.
    prefix : str
        Beamline Redis key prefix.
    author : str, optional
        ``updated_by`` for writes; defaults to ``staging_author()``.
    """

    def __init__(self, redis_client, prefix="", author=None):
        self._redis = redis_client
        self._prefix = prefix
        self.key = f"{prefix}{STAGING_QUEUE_TOPIC}"
        self.author = author or staging_author()

    @property
    def description(self):
        """Where the queue is kept, for the staging tab."""
        return f"Shared staging queue (Redis key {self.key})"

    @staticmethod
    def _parse(raw):
        if raw is None:
            return 0, []
        data = orjson.loads(raw)
        return int(data.get("version", 0)), list(data.get("items", []))

    def load(self):
        """
        Read the stored queue.

        Returns
        -------
        tuple of (int, list)
            Version and queue items.
        """
        return self._parse(self._redis.get(self.key))

    def save(self, items, base_version):
        """
        Store the queue if nobody changed it since ``base_version``.

        Parameters
        ----------
        items : list of dict
            Queue items to store.
        base_version : int
            Version the change was made on.

        Returns
        -------
        int
            The new version.

        Raises
        ------
        StagingConflict
            If the stored version is not ``base_version``.
        """
        import redis

        with self._redis.pipeline() as pipe:
            try:
                pipe.watch(self.key)
                current, _ = self._parse(pipe.get(self.key))
                if current != base_version:
                    raise StagingConflict(
                        f"staging queue is at version {current}, not {base_version}"
                    )
                new_version = base_version + 1
                data = {
                    "version": new_version,
                    "items": copy.deepcopy(list(items)),
                    "updated": time.time(),
                    "updated_by": self.author,
                }
                pipe.multi()
                pipe.set(
                    self.key, orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY)
                )
                pipe.execute()
            except redis.WatchError as e:
                raise StagingConflict("staging queue changed during the write") from e
        return new_version

    def watch(self, receiver):
        """
        Call ``receiver(key, event)`` on Redis changes under the prefix.

        Parameters
        ----------
        receiver : callable
            A bound method of a QObject living in the Qt main thread, so the
            call is queued to that thread. It must filter on ``self.key``.
        """
        from .QtRedisJSONDict import RedisWatcherThread

        watcher = RedisWatcherThread.get_or_create(self._redis, self._prefix)
        watcher.change_detected.connect(receiver)


def make_staging_store(user_status):
    """
    The staging store for this GUI's beamline Redis.

    Parameters
    ----------
    user_status : nbs_gui.models.UserStatus or None
        The GUI's status model, holding the beamline Redis client.

    Returns
    -------
    tuple of (RedisStagingStore or None, str)
        The store, or None and why the staging queue stays local.
    """
    client = getattr(user_status, "_redis_client", None)
    if client is None:
        return None, "no beamline Redis settings in beamline.toml"
    try:
        client.ping()
    except Exception as e:
        return None, f"beamline Redis unreachable ({e})"
    return RedisStagingStore(client, getattr(user_status, "_redis_prefix", "")), ""
