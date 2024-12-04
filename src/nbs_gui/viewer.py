from bluesky_widgets.models.run_engine_client import RunEngineClient
from bluesky_widgets.qt import Window
from bluesky_widgets.qt.threading import wait_for_workers_to_quit, active_thread_count
from .models import UserStatus
from .confEdit import ConfigEditor
from .load import instantiateGUIDevice
from nbs_core.autoload import loadFromConfig, simpleResolver
from nbs_core.autoconf import generate_device_config

from .settings import SETTINGS
from .mainWidget import QtViewer
from .widgets.header import Header

from qtpy.QtWidgets import QAction, QApplication, QVBoxLayout, QWidget

import pkg_resources


class CustomWindow(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("CustomWindow created")

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        self._qt_center.layout().addWidget(self.main_widget)
        print("Done With CustomWindow init")

    def update_widget(self, new_qt_widget, model):
        # Remove all widgets from the main layout

        config = SETTINGS.gui_config

        # Load the header from the entrypoint
        header_entrypoint = config.get("gui", {}).get("header", "nbs-gui-header")
        print(f"Attempting to load {header_entrypoint}")
        HeaderClass = self.load_header_from_entrypoint(header_entrypoint)

        for i in reversed(range(self.main_layout.count())):
            self.main_layout.itemAt(i).widget().setParent(None)

        # Add the new header
        self.header = HeaderClass(model)
        self.main_layout.addWidget(self.header)

        # Add the new tabbed widget
        self.main_layout.addWidget(new_qt_widget)

        # Update the reference
        self.qt_widget = new_qt_widget

    @staticmethod
    def load_header_from_entrypoint(entrypoint_name):
        for entry_point in pkg_resources.iter_entry_points(group="nbs_gui.widgets"):
            if entry_point.name == entrypoint_name:
                print(f"Loading {entry_point.name}")
                return entry_point.load()
        print(
            f"Warning: Header entrypoint '{entrypoint_name}' not found. Using default Header."
        )
        return Header


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


class Viewer(ViewerModel):
    """
    This extends the model by attaching a Qt Window as its view.

    This object is meant to be exposed to the user in an interactive console.
    """

    def __init__(self, *, show=True):
        super().__init__()
        self.init_ui(show)

    def init_ui(self, show):
        print("Initializing UI")
        self._widget = QtViewer(self)
        self._window = CustomWindow(self._widget, show=show)
        print("Updating CustomWindow")
        self._window.update_widget(self._widget, self)

        menu_bar = self._window._qt_window.menuBar()
        menu_item_control = menu_bar.addMenu("Control Actions")
        self.action_activate_env_destroy = QAction(
            "Activate 'Destroy Environment'", self._window._qt_window
        )
        self.action_activate_env_destroy.setCheckable(True)
        self._update_action_env_destroy_state()
        self.action_activate_env_destroy.triggered.connect(
            self._activate_env_destroy_triggered
        )
        menu_item_control.addAction(self.action_activate_env_destroy)

        menu_item_config = self._window._qt_window.menuBar().addMenu("Config")
        self.action_edit_config = QAction("Edit Config", self._window._qt_window)
        self.action_edit_config.triggered.connect(self.editConfig)
        menu_item_config.addAction(self.action_edit_config)

        self.action_reload_config = QAction("Reload Config", self._window._qt_window)
        self.action_reload_config.triggered.connect(self.reloadConfig)
        menu_item_config.addAction(self.action_reload_config)

        self._widget.model.run_engine.events.status_changed.connect(
            self.on_update_widgets
        )
        print("Finished Initializing Viewer")

    def editConfig(self):
        self.config_editor = ConfigEditor(SETTINGS.config)
        self.config_editor.show()

    def reloadConfig(self):
        self.init_beamline()
        new_widget = QtViewer(self)
        self._window.update_widget(new_widget, self)
        self._widget = new_widget

    def _update_action_env_destroy_state(self):
        env_destroy_activated = self._widget.model.run_engine.env_destroy_activated
        self.action_activate_env_destroy.setChecked(env_destroy_activated)

    def _activate_env_destroy_triggered(self):
        env_destroy_activated = self._widget.model.run_engine.env_destroy_activated
        self._widget.model.run_engine.activate_env_destroy(not env_destroy_activated)

    def on_update_widgets(self, event):
        self._update_action_env_destroy_state()

    @property
    def window(self):
        return self._window

    def show(self):
        """Resize, show, and raise the window."""
        self._window.show()

    def close(self):
        """Close the window."""
        print("In close method")
        self._window.close()
        print("After window close in close method")
