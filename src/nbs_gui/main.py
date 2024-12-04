import argparse
import os
from os.path import join, dirname, exists
import toml

from bluesky_widgets.qt import gui_qt
from .viewer import Viewer
from .settings import SETTINGS, get_ipython_startup_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description="SST Queue Monitor")

    # Create mutually exclusive group for profile and minimal config
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        "--profile",
        help="Location of config file to load Ophyd objects from",
    )
    config_group.add_argument(
        "--minimal-config",
        action="store_true",
        help="Use a minimal configuration without requiring a profile or config files.",
    )

    # Other optional arguments
    parser.add_argument(
        "--zmq-control-addr",
        default=None,
        help="Address of control socket of RE Manager, e.g. tcp://localhost:60615. "
        "If the address is passed as a CLI parameter, it overrides the address specified with "
        "QSERVER_ZMQ_CONTROL_ADDRESS environment variable. Default address is "
        "used if the parameter or the environment variable are not specified.",
    )
    parser.add_argument(
        "--zmq-control",
        default=None,
        help="The parameter is deprecated and will be removed. Use --zmq-control-addr instead.",
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
        "--zmq-publish",
        default=None,
        help="The parameter is deprecated and will be removed. Use --zmq-info-addr instead.",
    )
    parser.add_argument(
        "--http-server-uri",
        default=None,
        help="Address of HTTP Server, e.g. 'http://localhost:60610'. Activates communication "
        "with Queue Server via HTTP server. If the address is passed as a CLI parameter, "
        "it overrides the address specified with QSERVER_HTTP_SERVER_URI environment variable. "
        "Use QSERVER_HTTP_SERVER_API_KEY environment variable to pass an API key for authorization.",
    )
    parser.add_argument(
        "--no-devices",
        action="store_true",
        help="Skip loading the devices configuration file",
    )
    parser.add_argument(
        "--ipython-dir",
        default=None,
        help="Location of the ipython dir, if different from the default",
    )

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
    args = parser.parse_args(argv)

    # The priority is first to check if an address is passed as a parameter and then
    #   check if the environment variables are set. Otherwise use the default local addresses.
    #   (The default addresses are typically used in demos.)
    zmq_control_addr = args.zmq_control_addr
    zmq_control_addr = zmq_control_addr or args.zmq_control
    if args.zmq_control is not None:
        print(
            "The parameter --zmq-control is deprecated and will be removed. Use --zmq-control-addr instead."
        )
    zmq_control_addr = zmq_control_addr or os.environ.get(
        "QSERVER_ZMQ_CONTROL_ADDRESS", None
    )

    zmq_info_addr = args.zmq_info_addr
    if args.zmq_publish is not None:
        print(
            "The parameter --zmq-publish is deprecated and will be removed. Use --zmq-info-addr instead."
        )
    zmq_info_addr = zmq_info_addr or args.zmq_publish
    zmq_info_addr = zmq_info_addr or os.environ.get("QSERVER_ZMQ_INFO_ADDRESS", None)
    if "QSERVER_ZMQ_PUBLISH_ADDRESS" in os.environ:
        print(
            "WARNING: Environment variable QSERVER_ZMQ_PUBLISH_ADDRESS is deprecated and will be removed."
        )
        print("    Use QSERVER_ZMQ_INFO_ADDRESS environment variable instead.")
    zmq_info_addr = zmq_info_addr or os.environ.get("QSERVER_ZMQ_PUBLISH_ADDRESS", None)

    http_server_uri = args.http_server_uri
    http_server_uri = http_server_uri or os.environ.get("QSERVER_HTTP_SERVER_URI", None)

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

    if args.minimal_config:
        print("Using minimal configuration")
        SETTINGS.gui_config = {
            "gui": {
                "header": "nbs-gui-header",
                "tabs": {
                    "include": ["nbs-gui-queue", "nbs-gui-console", "kafka-table-tab"]
                },
                "plans": {"load_plans": False},
            },
            "kafka": {"config_file": args.kafka_config, "bl_acronym": args.beamline},
        }
        SETTINGS.object_config = {}
        SETTINGS.beamline_config = {}
    else:
        profile_dir = get_ipython_startup_dir(args.profile, args.ipython_dir)
        SETTINGS.object_config_file = join(profile_dir, "devices.toml")
        SETTINGS.gui_config_file = join(profile_dir, "gui_config.toml")
        SETTINGS.beamline_config_file = join(profile_dir, "beamline.toml")

        if exists(SETTINGS.gui_config_file):
            with open(SETTINGS.gui_config_file, "r") as config_file:
                SETTINGS.gui_config = toml.load(config_file)
        else:
            SETTINGS.gui_config = {}

        if not args.no_devices and exists(SETTINGS.object_config_file):
            with open(SETTINGS.object_config_file, "r") as config_file:
                SETTINGS.object_config = toml.load(config_file)
        else:
            SETTINGS.object_config = {}

        if exists(SETTINGS.beamline_config_file):
            with open(SETTINGS.beamline_config_file, "r") as config_file:
                SETTINGS.beamline_config = toml.load(config_file)
        else:
            SETTINGS.beamline_config = {}

    with gui_qt("BlueSky Queue Monitor"):
        viewer = Viewer()  # noqa: 401


if __name__ == "__main__":
    main()
