from qtpy.QtWidgets import QWidget, QPushButton, QGroupBox, QVBoxLayout, QMessageBox
from qtpy.QtCore import Signal, Slot
from qtpy.QtCore import Qt
import time


class QueueServerControls(QWidget):
    """
    A compact widget for controlling Queue Server connection and environment.
    Combines connection and environment controls into a single widget.
    """

    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._stop = False

        # Create widgets
        # self._lb_status = QLabel("OFFLINE")
        self._pb_connect = QPushButton("Connect")
        self._pb_env = QPushButton("Open")
        self._pb_destroy = QPushButton("Destroy")

        # Disable environment and destroy buttons initially
        self._pb_env.setEnabled(False)
        self._pb_destroy.setEnabled(False)

        # Connect signals
        self._pb_connect.clicked.connect(self._pb_connect_clicked)
        self._pb_env.clicked.connect(self._pb_env_clicked)
        self._pb_destroy.clicked.connect(self._pb_destroy_clicked)

        # Create layout
        self._group_box = QGroupBox("Queue Server")
        vbox = QVBoxLayout()
        # vbox.addWidget(self._lb_status, alignment=Qt.AlignHCenter)
        vbox.addWidget(self._pb_connect)
        vbox.addWidget(self._pb_env)
        vbox.addWidget(self._pb_destroy)
        self._group_box.setLayout(vbox)

        outer_vbox = QVBoxLayout()
        outer_vbox.setAlignment(Qt.AlignTop)
        outer_vbox.setContentsMargins(5, 5, 5, 5)

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
        self.destroyed.connect(self._cleanup)

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

        # Destroy button is always enabled when connected
        self._pb_destroy.setEnabled(is_connected)

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

    def _pb_destroy_clicked(self):
        """Handle destroy environment button clicks"""
        # Show confirmation dialog
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirm Environment Destruction")
        msg_box.setText("Are you sure you want to destroy the RE Worker environment?")
        msg_box.setInformativeText(
            "This action will forcefully terminate the environment and may result "
            "in data loss. This should only be used when the environment is "
            "frozen or unresponsive."
        )
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        if msg_box.exec() == QMessageBox.Yes:
            try:
                # Work around upstream bug: copy environment_destroy logic here
                # Check if RE Worker environment already exists and RE manager is idle.
                self.model.load_re_manager_status()
                status = self.model.re_manager_status
                if not status["worker_environment_exists"]:
                    raise RuntimeError("RE Worker environment does not exist")

                # Initiate destruction of RE Worker environment
                try:
                    self.model._client.environment_destroy()
                except Exception as ex:
                    raise RuntimeError(
                        f"Failed to destroy RE Worker environment: {ex}"
                    ) from ex

                # Wait for the environment to be destroyed.
                t_stop = time.time() + 30  # 30 second timeout
                while True:
                    self.model.load_re_manager_status()
                    status2 = self.model.re_manager_status
                    if (
                        not status2["worker_environment_exists"]
                        and status2["manager_state"] == "idle"
                    ):
                        break
                    if time.time() > t_stop:
                        raise RuntimeError(
                            "Failed to destroy RE Worker: timeout occurred"
                        )
                    time.sleep(0.5)

            except Exception as ex:
                print(f"Exception destroying environment: {ex}")

    def _start_thread(self):
        """Start the status update thread"""
        from bluesky_widgets.qt.threading import FunctionWorker

        self._thread = FunctionWorker(self._reload_status)
        self._thread.finished.connect(self._reload_complete)
        self._thread.start()

    def _cleanup(self, *args):
        """Disconnect callbacks to avoid emitting into deleted Qt objects."""
        self._stop = True
        self._deactivate_updates = True
        try:
            self.model.events.status_changed.disconnect(self.on_update_widgets)
        except Exception:
            pass
        try:
            self.signal_update_widget.disconnect(self.slot_update_widgets)
        except Exception:
            pass

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

    def teardown(self):
        """
        Disconnect callbacks and stop updates for reload.

        Returns
        -------
        None
        """
        self._stop = True
        self._deactivate_updates = True
        try:
            self.model.events.status_changed.disconnect(self.on_update_widgets)
        except Exception:
            pass
        try:
            self.signal_update_widget.disconnect(self.slot_update_widgets)
        except Exception:
            pass
        try:
            self.destroyed.disconnect(self._cleanup)
        except Exception:
            pass
