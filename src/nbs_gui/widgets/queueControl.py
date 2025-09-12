from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QFormLayout,
    QFrame,
)
from qtpy.QtCore import Qt, Signal, Slot


class QtReQueueControls(QWidget):
    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        self._status_queue_autostart_enabled = False

        # Combined Start/Stop button
        self._pb_queue_start_stop = QPushButton("Start")
        self._pb_queue_start_stop.setEnabled(False)
        self._pb_queue_start_stop.setCheckable(True)
        self._pb_queue_start_stop.clicked.connect(self._pb_queue_start_stop_clicked)

        self._pb_queue_exec_one = QPushButton("Execute One Plan")
        self._pb_queue_exec_one.setEnabled(False)
        self._pb_queue_exec_one.clicked.connect(self._pb_queue_exec_one_clicked)

        self._cb_queue_autostart = QCheckBox("Auto")
        self._cb_queue_autostart.setEnabled(False)
        self._cb_queue_autostart.stateChanged.connect(
            self._cb_queue_autostart_state_changed
        )

        self._group_box = QGroupBox("Queue")

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(self._pb_queue_start_stop)
        hbox.addWidget(self._cb_queue_autostart)
        vbox.addLayout(hbox)
        vbox.addWidget(self._pb_queue_exec_one)

        self._group_box.setLayout(vbox)

        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignTop)
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.addWidget(self._group_box)
        self.setLayout(vbox)

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widget.connect(self.slot_update_widgets)

    def on_update_widgets(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        self.signal_update_widget.emit(is_connected, status)

    @Slot(bool, object)
    def slot_update_widgets(self, is_connected, status):
        worker_exists = status.get("worker_environment_exists", False)
        running_item_uid = status.get("running_item_uid", None)
        queue_stop_pending = status.get("queue_stop_pending", False)
        queue_autostart_enabled = status.get("queue_autostart_enabled", False)

        self._status_queue_autostart_enabled = queue_autostart_enabled

        pb_queue_start_enabled = (
            is_connected and worker_exists and not bool(running_item_uid)
        )
        pb_queue_stop_enabled = (
            is_connected and worker_exists and bool(running_item_uid)
        )

        # Update button state and label
        if pb_queue_stop_enabled:
            self._pb_queue_start_stop.setText("Stop")
            if queue_stop_pending:
                self._pb_queue_start_stop.setChecked(True)
            else:
                self._pb_queue_start_stop.setChecked(False)
        else:
            self._pb_queue_start_stop.setText("Start")
            self._pb_queue_start_stop.setChecked(False)

        self._pb_queue_start_stop.setEnabled(
            pb_queue_start_enabled or pb_queue_stop_enabled
        )
        self._pb_queue_exec_one.setEnabled(pb_queue_start_enabled)

        cb_enabled = is_connected and worker_exists
        cb_checked = cb_enabled and queue_autostart_enabled
        self._cb_queue_autostart.setEnabled(cb_enabled)
        self._cb_queue_autostart.setChecked(True if cb_checked else False)

    def _pb_queue_start_stop_clicked(self):
        """Handle Start/Stop button clicks"""
        try:
            # If text is "Stop", we want to stop the queue
            if self._pb_queue_start_stop.text() == "Stop":
                if self._pb_queue_start_stop.isChecked():
                    self.model.queue_stop()
                else:
                    self.model.queue_stop_cancel()
            else:
                self.model.queue_start()
        except Exception as ex:
            QMessageBox.critical(
                self,
                "Queue Control Error",
                f"Failed to {'stop' if self._pb_queue_start_stop.text() == 'Stop' else 'start'} queue: {str(ex)}",
                QMessageBox.Ok,
            )

    def _pb_queue_exec_one_clicked(self):
        if self.model.re_manager_status.get("manager_state", None) != "idle":
            QMessageBox.critical(
                self,
                "Queue Control Error",
                "RE Manager is not idle. Please stop the queue before executing one plan.",
                QMessageBox.Ok,
            )
            return
        try:
            resp = self.model._client.item_remove(pos="front")
            if resp["success"]:
                self.model._client.item_execute(resp["item"])
        except Exception as ex:
            QMessageBox.critical(
                self,
                "Queue Control Error",
                f"Failed to execute one plan: {str(ex)}",
                QMessageBox.Ok,
            )

    def _cb_queue_autostart_state_changed(self, state):
        try:
            enable = state == Qt.Checked
            if enable != self._status_queue_autostart_enabled:
                self._status_queue_autostart_enabled = enable
                self.model.queue_autostart(enable=enable)
        except Exception as ex:
            print(f"Exception: {ex}")


class QtReStatusMonitor(QWidget):
    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        # Add connection status label
        self._lb_connection_status = QLabel("-")

        # Create value labels separately from their text labels
        self._lb_environment_exists = QLabel("-")
        self._lb_manager_state = QLabel("-")
        self._lb_re_state = QLabel("-")
        self._lb_items_in_history = QLabel("-")
        self._lb_queue_autostart_enabled = QLabel("-")
        self._lb_queue_stop_pending = QLabel("-")
        self._lb_items_in_queue = QLabel("-")
        self._lb_queue_loop_mode = QLabel("-")

        self._group_box = QGroupBox("RE Manager Status")
        hbox = QHBoxLayout()
        hbox.setSpacing(15)
        hbox.setContentsMargins(5, 5, 5, 5)

        # Environment form
        env_form = QFormLayout()
        env_form.setVerticalSpacing(1)
        env_form.setHorizontalSpacing(5)
        env_form.setLabelAlignment(Qt.AlignRight)  # Right-align labels
        env_form.addRow("Connection:", self._lb_connection_status)
        env_form.addRow("RE Environment:", self._lb_environment_exists)
        env_form.addRow("Manager state:", self._lb_manager_state)
        hbox.addLayout(env_form)

        # Add vertical line
        # line1 = QFrame()
        # line1.setFrameShape(QFrame.VLine)
        # line1.setFrameShadow(QFrame.Sunken)
        # hbox.addWidget(line1)

        # Queue status form
        queue_form = QFormLayout()
        queue_form.setVerticalSpacing(1)
        queue_form.setHorizontalSpacing(5)
        queue_form.setLabelAlignment(Qt.AlignRight)
        queue_form.addRow("Queue AUTOSTART:", self._lb_queue_autostart_enabled)
        queue_form.addRow("Queue STOP pending:", self._lb_queue_stop_pending)
        queue_form.addRow("Queue LOOP mode:", self._lb_queue_loop_mode)
        hbox.addLayout(queue_form)

        # Add vertical line
        # line2 = QFrame()
        # line2.setFrameShape(QFrame.VLine)
        # line2.setFrameShadow(QFrame.Sunken)
        # hbox.addWidget(line2)

        # Items status form
        items_form = QFormLayout()
        items_form.setVerticalSpacing(1)
        items_form.setHorizontalSpacing(10)
        items_form.setLabelAlignment(Qt.AlignRight)
        items_form.addRow("RE state:", self._lb_re_state)
        items_form.addRow("Items in queue:", self._lb_items_in_queue)
        items_form.addRow("Items in history:", self._lb_items_in_history)
        hbox.addLayout(items_form)

        self._group_box.setLayout(hbox)

        vbox = QVBoxLayout()
        vbox.addWidget(self._group_box)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setContentsMargins(5, 5, 5, 5)
        self.setLayout(vbox)

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widget.connect(self.slot_update_widgets)

    def _set_label_text(self, label, value):
        """Set label text with a default for None values"""
        if value is None:
            value = "-"
        label.setText(str(value))

    def on_update_widgets(self, event):
        status = event.status
        is_connected = bool(event.is_connected)
        self.signal_update_widget.emit(is_connected, status)

    @Slot(bool, object)
    def slot_update_widgets(self, is_connected, status):
        # Update connection status
        self._set_label_text(
            self._lb_connection_status, "ONLINE" if is_connected else "OFFLINE"
        )
        if not is_connected:
            status = {}
        worker_exists = status.get("worker_environment_exists", None)
        manager_state = status.get("manager_state", None)
        re_state = status.get("re_state", None)
        items_in_history = status.get("items_in_history", None)
        items_in_queue = status.get("items_in_queue", None)
        queue_autostart_enabled = bool(status.get("queue_autostart_enabled", False))
        queue_stop_pending = status.get("queue_stop_pending", None)

        queue_mode = status.get("plan_queue_mode", None)
        queue_loop_enabled = queue_mode.get("loop", None) if queue_mode else None

        # Capitalize state of RE Manager
        manager_state = (
            manager_state.upper() if isinstance(manager_state, str) else manager_state
        )
        re_state = re_state.upper() if isinstance(re_state, str) else re_state

        self._set_label_text(
            self._lb_environment_exists, "OPEN" if worker_exists else "CLOSED"
        )
        self._set_label_text(self._lb_manager_state, manager_state)
        self._set_label_text(self._lb_re_state, re_state)
        self._set_label_text(self._lb_items_in_history, str(items_in_history))
        self._set_label_text(self._lb_items_in_queue, str(items_in_queue))
        self._set_label_text(
            self._lb_queue_autostart_enabled, "ON" if queue_autostart_enabled else "OFF"
        )
        self._set_label_text(
            self._lb_queue_stop_pending, "YES" if queue_stop_pending else "NO"
        )
        self._set_label_text(
            self._lb_queue_loop_mode, "ON" if queue_loop_enabled else "OFF"
        )
