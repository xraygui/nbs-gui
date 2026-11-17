"""Test setup shared by the nbs-gui tests."""

import sys
import types

# nbs_bl.redisUtils imports nslsii.utils, which the pinned nslsii (<0.12) lacks;
# the tests pass their own Redis clients, so a stand-in module is enough.
try:
    import nbs_bl.redisUtils  # noqa: F401
except ImportError:
    stub = types.ModuleType("nbs_bl.redisUtils")

    def open_redis_client_from_settings(settings):
        raise RuntimeError("nbs_bl.redisUtils is not importable in this environment")

    stub.open_redis_client_from_settings = open_redis_client_from_settings
    sys.modules["nbs_bl.redisUtils"] = stub
