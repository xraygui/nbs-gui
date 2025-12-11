from bluesky_widgets.qt import Window

from .settings import SETTINGS
from .widgets.header import Header
from .mainWidget import TabViewer
from .confEdit import ConfigEditor
from qtpy.QtWidgets import QVBoxLayout, QWidget, QAction

from importlib.metadata import entry_points


class MainWindow(Window):
    """
    Main application window that manages the UI components and menu actions.


    """

    def __init__(self, model, *, show=True):
        super().__init__(TabViewer(model), show=show)
        self.model = model
        self._mode_model = None

        # Initialize main widget container
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        self._qt_center.layout().addWidget(self.main_widget)

        # Initialize UI components
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components including menus and widgets"""
        self.setup_menus()
        self.update_widget(self.qt_widget, self.model)

        # Connect model events
        self.model.run_engine.events.status_changed.connect(self.on_update_widgets)
        self._attach_mode_listener()

    def setup_menus(self):
        """Setup the application menu bar"""
        menu_bar = self._qt_window.menuBar()

        # Control Actions menu
        menu_item_control = menu_bar.addMenu("Control Actions")
        self.action_activate_env_destroy = QAction(
            "Activate 'Destroy Environment'", self._qt_window
        )
        self.action_activate_env_destroy.setCheckable(True)
        self._update_action_env_destroy_state()
        self.action_activate_env_destroy.triggered.connect(
            self._activate_env_destroy_triggered
        )
        menu_item_control.addAction(self.action_activate_env_destroy)

        # Config menu
        menu_item_config = menu_bar.addMenu("Config")
        self.action_edit_config = QAction("Edit Config", self._qt_window)
        self.action_edit_config.triggered.connect(self.edit_config)
        menu_item_config.addAction(self.action_edit_config)

        self.action_reload_config = QAction("Reload Config", self._qt_window)
        self.action_reload_config.triggered.connect(self.reload_config)
        menu_item_config.addAction(self.action_reload_config)

    def update_widget(self, new_qt_widget, model):
        """Update the main widget with a new widget and header"""
        config = SETTINGS.gui_config
        header_entrypoint = config.get("gui", {}).get("header", "nbs-gui-header")
        print(f"Loading header from {header_entrypoint}")
        HeaderClass = self.load_header_from_entrypoint(header_entrypoint)

        # Clear existing widgets
        for i in reversed(range(self.main_layout.count())):
            self.main_layout.itemAt(i).widget().setParent(None)

        # Add new widgets
        self.header = HeaderClass(model)
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(new_qt_widget)
        self.qt_widget = new_qt_widget

    def edit_config(self):
        """Open the configuration editor"""
        self.config_editor = ConfigEditor(SETTINGS.config)
        self.config_editor.show()

    def reload_config(self):
        """Reload the configuration and update the UI"""
        self.model.init_beamline()
        new_widget = TabViewer(self.model)
        self.update_widget(new_widget, self.model)
        self._attach_mode_listener()

    def _update_action_env_destroy_state(self):
        """Update the state of the environment destroy action"""
        env_destroy_activated = self.qt_widget.model.run_engine.env_destroy_activated
        self.action_activate_env_destroy.setChecked(env_destroy_activated)

    def _activate_env_destroy_triggered(self):
        """Handle the environment destroy action being triggered"""
        env_destroy_activated = self.qt_widget.model.run_engine.env_destroy_activated
        self.qt_widget.model.run_engine.activate_env_destroy(not env_destroy_activated)

    def on_update_widgets(self, event):
        """Handle widget updates when model changes"""
        self._update_action_env_destroy_state()

    def _attach_mode_listener(self):
        """Connect to mode change signal to rebuild UI on mode switch."""
        if self._mode_model is not None:
            try:
                self._mode_model.mode_changed.disconnect(self._handle_mode_change)
            except Exception:
                pass
            self._mode_model = None

        beamline = getattr(self.model, "beamline", None)
        mode_model = getattr(beamline, "mode_model", None)
        if mode_model is not None:
            try:
                mode_model.mode_changed.connect(self._handle_mode_change)
                self._mode_model = mode_model
            except Exception as e:
                print(f"Failed to connect mode change listener: {e}")

    def _handle_mode_change(self, mode):
        """Rebuild beamline and UI when mode changes."""
        try:
            self._reload_in_place(mode)
        except Exception as e:
            print(f"Error handling mode change rebuild: {e}")

    @staticmethod
    def load_header_from_entrypoint(entrypoint_name):
        """Load the header widget from an entry point"""
        for entry_point in entry_points(group="nbs_gui.widgets"):
            if entry_point.name == entrypoint_name:
                return entry_point.load()
        return Header

    def _reload_in_place(self, mode):
        """
        Reload beamline devices and refresh reloadable tabs.

        Parameters
        ----------
        mode : str
            Target mode.
        """
        self.model.reload_beamline_for_mode_inplace(mode)
        if hasattr(self.qt_widget, "reload_tabs"):
            self.qt_widget.reload_tabs(self.model)
        self._attach_mode_listener()
        self._update_action_env_destroy_state()
