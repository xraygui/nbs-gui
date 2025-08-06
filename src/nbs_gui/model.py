"""Main model for the GUI application."""

from bluesky_widgets.models.run_engine_client import RunEngineClient
from .models import UserStatus
from .models.QtReQueueStaging import QueueStagingModel
from nbs_core.autoconf import generate_device_config
from nbs_core.autoload import simpleResolver

from .settings import SETTINGS


class ViewerModel:
    """This encapsulates all the models in the application."""

    def __init__(self):
        print("Initializing ViewerModel")
        self.init_beamline()
        self.init_queue_staging()

    def init_beamline(self):
        """Initialize beamline model and connections."""
        print("Initializing Beamline")
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

        self.user_status = UserStatus(self.run_engine, redis_settings=redis_settings)

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

            # Create beamline model with config
            self.beamline = BeamlineModel(config)
        else:
            self.beamline = None

        self.settings = SETTINGS

    def init_queue_staging(self):
        """Initialize queue staging model."""
        print("Initializing Queue Staging")
        self.queue_staging = QueueStagingModel(self.run_engine)
