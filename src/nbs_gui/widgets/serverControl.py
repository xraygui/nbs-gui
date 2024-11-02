from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
)
from qtpy.QtCore import Signal, Slot, Qt


class QueueServerControls(QWidget):
    """
    A compact widget for controlling Queue Server connection and environment.
    Combines connection and environment controls into a single widget.
    """

    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        # Create widgets
        # self._lb_status = QLabel("OFFLINE")
        self._pb_connect = QPushButton("Connect")
        self._pb_env = QPushButton("Open")

        # Disable environment button initially
        self._pb_env.setEnabled(False)

        # Connect signals
        self._pb_connect.clicked.connect(self._pb_connect_clicked)
        self._pb_env.clicked.connect(self._pb_env_clicked)

        # Create layout
        self._group_box = QGroupBox("Queue Server")
        vbox = QVBoxLayout()
        # vbox.addWidget(self._lb_status, alignment=Qt.AlignHCenter)
        vbox.addWidget(self._pb_connect)
        vbox.addWidget(self._pb_env)
        self._group_box.setLayout(vbox)

        outer_vbox = QVBoxLayout()
        outer_vbox.setAlignment(Qt.AlignTop)
        outer_vbox.addWidget(self._group_box)
        self.setLayout(outer_vbox)

        # Thread used to initiate periodic status updates
        self._thread = None
        self.updates_activated = False
        self._deactivate_updates = False
        self.update_period = 1  # Status update period in seconds

        # Connect model signals
        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widget.connect(self.slot_update_widgets)

    def on_update_widgets(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        self.signal_update_widget.emit(is_connected, status)

    @Slot(bool, object)
    def slot_update_widgets(self, is_connected, status):
        # Update connection status label
        if is_connected:
            # self._lb_status.setText("ONLINE")
            self._pb_connect.setText("Disconnect")
        else:
            # self._lb_status.setText("OFFLINE")
            self._pb_connect.setText("Connect")

        # Update environment button state and text
        worker_exists = status.get("worker_environment_exists", False)
        manager_state = status.get("manager_state", None)

        if worker_exists:
            self._pb_env.setText("Close")
            self._pb_env.setEnabled(is_connected and manager_state == "idle")
        else:
            self._pb_env.setText("Open")
            self._pb_env.setEnabled(is_connected and manager_state == "idle")

    def _pb_connect_clicked(self):
        """Handle connect/disconnect button clicks"""
        if not self.updates_activated:
            # Connect
            self.updates_activated = True
            self._deactivate_updates = False
            self.model.clear_connection_status()
            self.model.manager_connecting_ops()
            self._start_thread()
        else:
            # Disconnect
            self._deactivate_updates = True

    def _pb_env_clicked(self):
        """Handle environment open/close button clicks"""
        try:
            if self._pb_env.text() == "Open":
                self.model.environment_open()
            else:
                self.model.environment_close()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _start_thread(self):
        """Start the status update thread"""
        from bluesky_widgets.qt.threading import FunctionWorker

        self._thread = FunctionWorker(self._reload_status)
        self._thread.finished.connect(self._reload_complete)
        self._thread.start()

    def _reload_complete(self):
        """Handle completion of status update thread"""
        if not self._deactivate_updates:
            self._start_thread()
        else:
            self.model.clear_connection_status()
            self.updates_activated = False
            self._deactivate_updates = False

    def _reload_status(self):
        """Reload queue server status"""
        self.model.load_re_manager_status()
        import time

        time.sleep(self.update_period)
