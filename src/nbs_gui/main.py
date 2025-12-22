import argparse
import os
from os.path import join, dirname, exists

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from bluesky_widgets.qt import gui_qt
from .window import MainWindow
from .model import ViewerModel
from .settings import SETTINGS, get_ipython_startup_dir, set_top_level_model


def add_communication_args(parser):
    parser.add_argument(
        "--zmq-control-addr",
        default=None,
        help="Address of control socket of RE Manager, e.g. tcp://localhost:60615. "
        "If the address is passed as a CLI parameter, it overrides the address specified with "
        "QSERVER_ZMQ_CONTROL_ADDRESS environment variable. Default address is "
        "used if the parameter or the environment variable are not specified.",
    )
    parser.add_argument(
        "--zmq-info-addr",
        default=None,
        help="Address of PUB-SUB socket of RE Manager, e.g. 'tcp://localhost:60625'. "
        "If the address is passed as a CLI parameter, it overrides the address specified with "
        "QSERVER_ZMQ_INFO_ADDRESS environment variable. Default address is "
        "used if the parameter or the environment variable are not specified.",
    )
    parser.add_argument(
        "--http-server-uri",
        default=None,
        help="Address of HTTP Server, e.g. 'http://localhost:60610'. Activates communication "
        "with Queue Server via HTTP server. If the address is passed as a CLI parameter, "
        "it overrides the address specified with QSERVER_HTTP_SERVER_URI environment variable. "
        "Use QSERVER_HTTP_SERVER_API_KEY environment variable to pass an API key for authorization.",
    )


def configure_communication_settings(args):
    zmq_control_addr = args.zmq_control_addr or os.environ.get(
        "QSERVER_ZMQ_CONTROL_ADDRESS", None
    )
    zmq_info_addr = args.zmq_info_addr or os.environ.get(
        "QSERVER_ZMQ_INFO_ADDRESS", None
    )
    http_server_uri = args.http_server_uri or os.environ.get(
        "QSERVER_HTTP_SERVER_URI", None
    )
    http_server_api_key = os.environ.get("QSERVER_HTTP_SERVER_API_KEY", None)

    if http_server_uri:
        print("Initializing: communication with Queue Server via HTTP Server ...")
        SETTINGS.http_server_uri = http_server_uri
        SETTINGS.http_server_api_key = http_server_api_key
        SETTINGS.zmq_re_manager_control_addr = None
        SETTINGS.zmq_re_manager_info_addr = None
    else:
        print(
            "Initializing: communication with Queue Server directly via 0MQ sockets ..."
        )
        SETTINGS.http_server_uri = None
        SETTINGS.http_server_api_key = None
        SETTINGS.zmq_re_manager_control_addr = zmq_control_addr
        SETTINGS.zmq_re_manager_info_addr = zmq_info_addr


def minimal(argv=None):
    parser = argparse.ArgumentParser(description="Minimal NBS Queue Monitor")

    parser.add_argument(
        "--kafka-config",
        default="/etc/bluesky/kafka.yml",
        help="Path to Kafka configuration file. Default: /etc/bluesky/kafka.yml",
    )
    parser.add_argument(
        "--beamline",
        default="nbs",
        help="Beamline acronym (e.g., 'nbs', 'sst'). Default: nbs",
    )
    add_communication_args(parser)
    args = parser.parse_args(argv)

    configure_communication_settings(args)

    print("Using minimal configuration")
    SETTINGS.gui_config = {
        "gui": {
            "header": "nbs-gui-minimal-header",
            "tabs": {
                "include": ["nbs-gui-queue", "nbs-gui-console"]  # , "kafka-table-tab"]
            },
            "plans": {"load_plans": False},
        },
        # "kafka": {"config_file": args.kafka_config, "bl_acronym": args.beamline},
    }
    SETTINGS.object_config = {}
    SETTINGS.beamline_config = {}
    with gui_qt("Minimal NBS Queue Monitor"):
        model = ViewerModel()
        set_top_level_model(model)
        viewer = MainWindow(model)  # noqa: 401


def main(argv=None):
    parser = argparse.ArgumentParser(description="NBS Queue Monitor")

    # Create mutually exclusive group for profile and minimal config
    parser.add_argument(
        "--profile",
        help="Location of config file to load Ophyd objects from",
    )
    # Other optional arguments

    parser.add_argument(
        "--ipython-dir",
        default=None,
        help="Location of the ipython dir, if different from the default",
    )

    parser.add_argument(
        "--no-devices",
        default=False,
        action="store_true",
        help="Do not load a device file, even if one is present",
    )
    add_communication_args(parser)
    args = parser.parse_args(argv)

    configure_communication_settings(args)

    profile_dir = get_ipython_startup_dir(args.profile, args.ipython_dir)


    with gui_qt("NBS Queue Monitor"):
        model = ViewerModel(profile_dir, no_devices=args.no_devices)
        set_top_level_model(model)
        viewer = MainWindow(model)  # noqa: 401


if __name__ == "__main__":
    main()
