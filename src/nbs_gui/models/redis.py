"""GUI models for Redis-backed signals."""

from qtpy.QtCore import Signal

from .base import BaseModel


class RedisStatusProvider:
    """Adapter to present UserStatus as a provider for RedisDevice."""

    def __init__(self, user_status):
        self.user_status = user_status
        self._cache = {}

    def request_status_dict(self, name, use_redis=True):
        if name not in self._cache:
            dct = self.user_status.get_redis_dict(name)
            if dct is None:
                raise RuntimeError(f"Redis dict {name} unavailable from UserStatus")
            self._cache[name] = dct
        return self._cache[name]

    def request_status_list(self, name, use_redis=True):
        dct = self.request_status_dict("")
        return list(dct.get(name, []))

    def set_status_list(self, name, values, use_redis=True):
        values = list(values)
        dct = self.request_status_dict("")
        dct[name] = values
        return values

    def __getitem__(self, name):
        return self.request_status_dict(name)

    def __contains__(self, name):
        try:
            self.request_status_dict(name)
            return True
        except Exception:
            return False