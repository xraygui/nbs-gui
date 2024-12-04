from bluesky_widgets.qt.threading import FunctionWorker
from qtpy.QtCore import QObject
from bluesky_queueserver_api import BFunc
import time


class UserStatus(QObject):
    def __init__(self, runEngineClient, redis_settings=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.REClientModel = runEngineClient
        self.REClientModel.events.status_changed.connect(self.on_status_update)
        self._signal_registry = {}
        self._uid_registry = {}
        self._item_cache = {}
        self._thread = None
        self.updates_activated = False
        self.update_period = 1
        self._redis_settings = redis_settings
        self._status_dicts = {}
        self._signals = {}
        self._redis_client = None

        if redis_settings:
            self._init_redis_client()

    def _init_redis_client(self):
        """Initialize Redis client from settings"""
        import redis

        self._redis_client = redis.Redis(
            host=self._redis_settings["host"],
            port=self._redis_settings.get("port", 6379),
            db=self._redis_settings.get("db", 0),
        )
        self._redis_prefix = self._redis_settings.get("prefix", "")

    def get_redis_dict(self, topic=""):
        """
        Get a QtRedisJSONDict for a specific topic.

        Parameters
        ----------
        topic : str
            Topic for the Redis dictionary

        Returns
        -------
        QtRedisJSONDict
            A new Redis dictionary instance for the topic
        """
        from .QtRedisJSONDict import QtRedisJSONDict

        if self._redis_client is None and self._redis_settings:
            self._init_redis_client()

        if self._redis_client is None:
            return None

        return QtRedisJSONDict(
            self._redis_client, self._redis_prefix, topic, parent=self
        )

    def _start_thread(self):
        self._thread = FunctionWorker(self._reload_status)
        self._thread.finished.connect(self._reload_complete)
        self.updates_activated = True
        self._thread.start()

    def _reload_complete(self):
        if not self._deactivate_updates:
            self._start_thread()
        else:
            self.updates_activated = False
            self._deactivate_updates = False

    def get_update(self, key):
        function = BFunc("request_update", key)
        response = self.REClientModel._client.function_execute(
            function, run_in_background=True
        )
        self.REClientModel._client.wait_for_completed_task(response["task_uid"])
        reply = self.REClientModel._client.task_result(response["task_uid"])
        task_status = reply["status"]
        task_result = reply["result"]
        if task_status == "completed" and task_result.get("success", False):
            self._item_cache[key] = task_result["return_value"]
            return task_result["return_value"]
        else:
            raise ValueError("Update unsuccessful")

    def get_cached(self, key, default=None):
        return self._item_cache.get(key, default)

    def _reload_status(self):
        function = BFunc("get_status")
        response = self.REClientModel._client.function_execute(
            function, run_in_background=True
        )
        self.REClientModel._client.wait_for_completed_task(response["task_uid"])
        reply = self.REClientModel._client.task_result(response["task_uid"])
        task_status = reply["status"]
        task_result = reply["result"]
        if task_status == "completed" and task_result.get("success", False):
            user_status = task_result["return_value"]
        else:
            raise ValueError("Status did not load successfully")
        new_uids = {}

        for key, signal_list in self._signal_registry.items():
            new_uid = user_status.get(key, "")
            if new_uid != self._uid_registry.get(key, ""):
                update = self.get_update(key)
                for sig in signal_list:
                    sig.emit(update)
                new_uids[key] = new_uid
        self._uid_registry.update(new_uids)
        time.sleep(self.update_period)

    def register_signal(self, key, signal, emit_cached=True):
        if key in self._signal_registry:
            if signal not in self._signal_registry[key]:
                self._signal_registry[key].append(signal)
        else:
            self._signal_registry[key] = [signal]
        if emit_cached:
            value = self.get_cached(key)
            if value is not None:
                signal.emit(value)

    def on_status_update(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        worker_exists = status.get("worker_environment_exists", False)
        self._deactivate_updates = not is_connected or not worker_exists
        if not self._deactivate_updates and not self.updates_activated:
            self._start_thread()
