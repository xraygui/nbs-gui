from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QStackedWidget,
    QMenu,
    QMessageBox,
    QSizePolicy,
)
from qtpy.QtCore import Signal, Slot, Qt
from bluesky_widgets.qt.run_engine_client import QtReStatusMonitor


class PlanControls(QWidget):
    """
    A compact widget for controlling Queue Server plan execution.
    Provides essential controls (Pause/Resume/Abort) directly visible
    and additional controls in a dropdown menu.
    """

    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        # Set size policy to prevent vertical expansion
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Create stacked widget for primary actions
        self._stacked_widget = QStackedWidget()
        self._stacked_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._stacked_widget.layout().setContentsMargins(0, 0, 0, 0)

        # Create "Running" page with Pause button
        self._running_widget = QWidget()
        self._running_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._pb_plan_pause_deferred = QPushButton("Pause")
        self._pb_plan_pause_deferred.setFixedHeight(25)
        running_layout = QVBoxLayout()
        running_layout.addWidget(self._pb_plan_pause_deferred)
        running_layout.setSpacing(1)
        running_layout.setContentsMargins(2, 2, 2, 2)
        self._running_widget.setLayout(running_layout)

        # Create "Paused" page with Resume and Abort
        self._paused_widget = QWidget()
        self._paused_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._pb_plan_resume = QPushButton("Resume")
        self._pb_plan_abort = QPushButton("Abort")
        self._pb_plan_resume.setFixedHeight(25)
        self._pb_plan_abort.setFixedHeight(25)
        paused_layout = QHBoxLayout()
        paused_layout.addWidget(self._pb_plan_resume)
        paused_layout.addWidget(self._pb_plan_abort)
        paused_layout.setSpacing(1)
        paused_layout.setContentsMargins(2, 2, 2, 2)
        self._paused_widget.setLayout(paused_layout)

        # Add pages to stacked widget
        self._stacked_widget.addWidget(self._running_widget)
        self._stacked_widget.addWidget(self._paused_widget)

        # Create more options menu button
        self._more_button = QPushButton("More")
        self._more_button.setFixedHeight(25)
        self._menu = QMenu(self)
        self._more_button.setMenu(self._menu)

        # Add actions to menu
        self._actions = {
            "pause_immediate": self._menu.addAction("Pause: Immediate"),
            "stop": self._menu.addAction("Stop"),
            "halt": self._menu.addAction("Halt"),
            "kernel_interrupt": self._menu.addAction("Ctrl-C"),
        }

        # Layout
        self._group_box = QGroupBox("Plan Control")
        self._group_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        vbox = QVBoxLayout()
        vbox.addWidget(self._stacked_widget)
        vbox.addWidget(self._more_button)

        vbox.setAlignment(Qt.AlignTop)
        self._group_box.setLayout(vbox)

        outer_vbox = QVBoxLayout()
        outer_vbox.setAlignment(Qt.AlignTop)
        outer_vbox.setContentsMargins(5, 5, 5, 5)
        outer_vbox.addWidget(self._group_box)
        self.setLayout(outer_vbox)

        # Disable all controls initially
        self._pb_plan_pause_deferred.setEnabled(False)
        self._pb_plan_resume.setEnabled(False)
        self._pb_plan_abort.setEnabled(False)
        self._actions["pause_immediate"].setEnabled(False)
        self._actions["stop"].setEnabled(False)
        self._actions["halt"].setEnabled(False)
        self._actions["kernel_interrupt"].setEnabled(False)

        # Connect signals with error handling
        self._pb_plan_pause_deferred.clicked.connect(
            lambda: self._handle_action(
                lambda: self.model.re_pause(option="deferred"), "Failed to pause plan"
            )
        )
        self._pb_plan_resume.clicked.connect(
            lambda: self._handle_action(self.model.re_resume, "Failed to resume plan")
        )
        self._pb_plan_abort.clicked.connect(
            lambda: self._handle_action(self.model.re_abort, "Failed to abort plan")
        )

        self._actions["pause_immediate"].triggered.connect(
            lambda: self._handle_action(
                lambda: self.model.re_pause(option="immediate"),
                "Failed to pause plan immediately",
            )
        )
        self._actions["stop"].triggered.connect(
            lambda: self._handle_action(self.model.re_stop, "Failed to stop plan")
        )
        self._actions["halt"].triggered.connect(
            lambda: self._handle_action(self.model.re_halt, "Failed to halt plan")
        )
        self._actions["kernel_interrupt"].triggered.connect(
            lambda: self._handle_action(
                self.model.kernel_interrupt, "Failed to interrupt kernel"
            )
        )

        # Connect model signals (no error handling for automatic updates)
        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widget.connect(self.slot_update_widgets)

        # Initialize button states with current model status
        try:
            initial_status = {
                "worker_environment_exists": False,
                "manager_state": None,
                "re_state": None,
            }
            if hasattr(self.model, "status"):
                initial_status = self.model.status
            self.slot_update_widgets(
                bool(getattr(self.model, "is_connected", False)), initial_status
            )
        except Exception:
            # Silently ignore errors in automatic updates
            pass

    def _handle_action(self, action_func, error_message):
        """
        Execute an action with error handling and message box display.

        Parameters
        ----------
        action_func : callable
            The function to execute
        error_message : str
            Error message to display if action fails
        """
        try:
            action_func()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Control Error",
                f"{error_message}: {str(e)}",
                QMessageBox.Ok,
            )

    def on_update_widgets(self, event):
        """Handle status change events from the model"""
        try:
            is_connected = bool(event.is_connected)
            status = event.status
            self.signal_update_widget.emit(is_connected, status)
        except Exception:
            # Silently ignore errors in automatic updates
            pass

    @Slot(bool, object)
    def slot_update_widgets(self, is_connected, status):
        """Update widget states based on connection status"""
        try:
            worker_exists = status.get("worker_environment_exists", False)
            manager_state = status.get("manager_state", None)
            re_state = status.get("re_state", None)

            # Determine which page to show
            if manager_state == "paused":
                self._stacked_widget.setCurrentWidget(self._paused_widget)
            else:
                self._stacked_widget.setCurrentWidget(self._running_widget)

            # Enable/disable controls based on state
            pause_enable = manager_state == "executing_queue" or re_state == "running"
            resume_enable = manager_state == "paused"

            # Update main controls
            self._pb_plan_pause_deferred.setEnabled(
                is_connected and worker_exists and pause_enable
            )
            self._pb_plan_resume.setEnabled(
                is_connected and worker_exists and resume_enable
            )
            self._pb_plan_abort.setEnabled(
                is_connected and worker_exists and resume_enable
            )

            # Update menu actions
            self._actions["pause_immediate"].setEnabled(pause_enable)
            self._actions["stop"].setEnabled(resume_enable)
            self._actions["halt"].setEnabled(resume_enable)
            self._actions["kernel_interrupt"].setEnabled(
                is_connected
                and worker_exists
                and manager_state != "executing_queue"
                and re_state != "running"
            )
        except Exception:
            # Silently ignore errors in automatic updates
            pass
