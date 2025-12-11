"""Main model for the GUI application."""

from bluesky_widgets.models.run_engine_client import RunEngineClient
from .models import UserStatus
from .models.QtReQueueStaging import QueueStagingModel
from nbs_core.autoconf import generate_device_config
from nbs_core.autoload import simpleResolver
from nbs_bl.redisDevice import _RedisSignal

from .settings import SETTINGS
from .models.redis import RedisStatusProvider


class ViewerModel:
    """This encapsulates all the models in the application."""

    def __init__(self):
        print("Initializing ViewerModel")
        self._mode_override = None
        self.init_beamline()
        self.init_queue_staging()

    def init_beamline(self, mode_override=None):
        """Initialize beamline model and connections."""
        print("Initializing Beamline")
        if not hasattr(self, "run_engine") or self.run_engine is None:
            self.run_engine = RunEngineClient(
                zmq_control_addr=SETTINGS.zmq_re_manager_control_addr,
                zmq_info_addr=SETTINGS.zmq_re_manager_info_addr,
                http_server_uri=SETTINGS.http_server_uri,
                http_server_api_key=SETTINGS.http_server_api_key,
            )

            # Get Redis settings from beamline config
            redis_settings = (
                SETTINGS.beamline_config.get("settings", {})
                .get("redis", {})
                .get("info", {})
            )

            self.user_status = UserStatus(
                self.run_engine, redis_settings=redis_settings
            )
        # Provide Redis status provider to RedisDevice for GUI context
        try:
            _RedisSignal.set_default_status_provider(RedisStatusProvider(self.user_status))
        except Exception as e:
            print(f"Could not set RedisDevice status provider: {e}")

        if SETTINGS.object_config_file is not None:
            # Get beamline model class
            bl_model_path = (
                SETTINGS.gui_config.get("models", {})
                .get("beamline", {})
                .get("loader", "")
            )
            if bl_model_path:
                BeamlineModel = simpleResolver(bl_model_path)
            else:
                raise KeyError("No BeamlineModel specified in config")

            # Generate device config
            config = generate_device_config(
                SETTINGS.object_config_file, SETTINGS.gui_config_file
            )

            if mode_override is not None:
                self._mode_override = mode_override

            # Create beamline model with config
            self.beamline = BeamlineModel(config, mode_override=mode_override)
        else:
            self.beamline = None

        self.settings = SETTINGS

    def init_queue_staging(self):
        """Initialize queue staging model."""
        print("Initializing Queue Staging")
        self.queue_staging = QueueStagingModel(self.run_engine)

    def reload_beamline_for_mode(self, mode):
        """Reload beamline for a new mode without recreating RE client."""
        self.init_beamline(mode_override=mode)
        return self.beamline

    def reload_beamline_for_mode_inplace(self, mode):
        """
        Reload beamline devices in place for a new mode.

        Parameters
        ----------
        mode : str
            Target mode.

        Returns
        -------
        object
            The beamline instance after reload.
        """
        if hasattr(self.beamline, "reload_for_mode"):
            self.beamline.reload_for_mode(mode)
            return self.beamline
        return self.reload_beamline_for_mode(mode)
