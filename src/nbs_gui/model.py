from bluesky_widgets.models.run_engine_client import RunEngineClient
from .models import UserStatus
from .load import instantiateGUIDevice
from nbs_core.autoload import loadFromConfig, simpleResolver
from nbs_core.autoconf import generate_device_config

from .settings import SETTINGS


class ViewerModel:
    """
    This encapsulates on the models in the application.
    """

    def __init__(self):
        print("Initializing ViewerModel")
        self.init_beamline()

    def init_beamline(self):
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
            blModelPath = (
                SETTINGS.gui_config.get("models", {})
                .get("beamline", {})
                .get("loader", "")
            )
            if blModelPath != "":
                BeamlineModel = simpleResolver(blModelPath)
            else:
                # from .models.misc import BeamlineModel
                raise KeyError("No BeamlineModel given")
            config = generate_device_config(
                SETTINGS.object_config_file, SETTINGS.gui_config_file
            )
            devices, groups, roles = loadFromConfig(
                config, instantiateGUIDevice, load_pass="auto"
            )
            self.beamline = BeamlineModel(devices, groups, roles)
        else:
            self.beamline = None

        self.settings = SETTINGS
