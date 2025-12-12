from bluesky_widgets.qt.threading import FunctionWorker
from qtpy.QtCore import QObject, QTimer
from bluesky_queueserver_api import BFunc
import time


class UserStatus(QObject):
    def __init__(self, runEngineClient, redis_settings=None, *args, **kwargs):
        print("Initializing UserStatus")
        super().__init__(*args, **kwargs)
        self.REClientModel = runEngineClient
        self.REClientModel.events.status_changed.connect(self.on_status_update)
        self._signal_registry = {}
        self._uid_registry = {}
        self._item_cache = {}
        self._thread = None
        self._is_reloading = False
        self._deactivate_updates = False
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
        if self._is_reloading:
            return
        if self._thread is not None:
            try:
                if callable(getattr(self._thread, "isRunning", None)) and self._thread.isRunning():
                    return
            except Exception:
                pass
        self._thread = FunctionWorker(self._reload_status)
        self._thread.finished.connect(self._reload_complete)
        self.updates_activated = True
        self._thread.start()

    def _reload_complete(self):
        if self._deactivate_updates or not self._signal_registry:
            self.updates_activated = False
            self._deactivate_updates = False
            return
        QTimer.singleShot(int(self.update_period * 1000), self._start_thread)

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
        self._is_reloading = True
        try:
            function = BFunc("get_status")
            response = self.REClientModel._client.function_execute(
                function, run_in_background=True
            )
            # print("Reloading status")
            self.REClientModel._client.wait_for_completed_task(response["task_uid"])
            reply = self.REClientModel._client.task_result(response["task_uid"])
            task_status = reply["status"]
            task_result = reply["result"]
            if task_status == "completed" and task_result.get("success", False):
                user_status = task_result["return_value"]
            else:
                raise ValueError("Status did not load successfully")
            new_uids = {}
            # print(f"Signal registry: {self._signal_registry}")
            dead_keys = []
            for key, signal_list in list(self._signal_registry.items()):
                # print(f"Reloading status for {key}")
                new_uid = user_status.get(key, "")
                if new_uid != self._uid_registry.get(key, ""):
                    # print(f"Updating {key}")
                    update = self.get_update(key)
                    alive = []
                    for sig in list(signal_list):
                        try:
                            sig.emit(update)
                            alive.append(sig)
                        except Exception as emit_exc:
                            print(f"Signal emit failed for {key}: {emit_exc}")
                    if alive:
                        self._signal_registry[key] = alive
                    else:
                        dead_keys.append(key)
                    new_uids[key] = new_uid
                # print(f"Done with {key}")
            for key in dead_keys:
                self._signal_registry.pop(key, None)
            # print("Done reloading status")
            self._uid_registry.update(new_uids)
        except Exception as e:
            print(f"Error reloading status: {e}")
        finally:
            self._is_reloading = False
        self._is_reloading = False

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
        #print("UserStatus update event received")
        if self._is_reloading:
            return
        is_connected = bool(event.is_connected)
        status = event.status
        worker_exists = status.get("worker_environment_exists", False)
        self._deactivate_updates = not is_connected or not worker_exists
        if not self._deactivate_updates and not self.updates_activated:
            self._start_thread()
