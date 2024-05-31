from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QGroupBox,
)
from qtpy.QtCore import Qt, Signal, Slot


class QtReQueueControls(QWidget):
    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model

        self._status_queue_autostart_enabled = False

        self._lb_queue_state = QLabel("STOPPED")

        self._pb_queue_start = QPushButton("Start")
        self._pb_queue_start.setEnabled(False)
        self._pb_queue_start.clicked.connect(self._pb_queue_start_clicked)

        self._pb_queue_exec_one = QPushButton("Execute One Plan")
        self._pb_queue_exec_one.setEnabled(False)
        self._pb_queue_exec_one.clicked.connect(self._pb_queue_exec_one_clicked)

        self._cb_queue_autostart = QCheckBox("Auto")
        self._cb_queue_autostart.setEnabled(False)
        self._cb_queue_autostart.stateChanged.connect(
            self._cb_queue_autostart_state_changed
        )

        self._pb_queue_stop = QPushButton("Stop")
        self._pb_queue_stop.setEnabled(False)
        self._pb_queue_stop.setCheckable(True)
        self._pb_queue_stop.clicked.connect(self._pb_queue_stop_clicked)

        self._group_box = QGroupBox("Queue")

        vbox = QVBoxLayout()
        vbox.addWidget(self._lb_queue_state, alignment=Qt.AlignHCenter)
        hbox = QHBoxLayout()
        hbox.addWidget(self._pb_queue_start)
        hbox.addWidget(self._cb_queue_autostart)
        vbox.addLayout(hbox)
        vbox.addWidget(self._pb_queue_exec_one)
        vbox.addWidget(self._pb_queue_stop)

        self._group_box.setLayout(vbox)

        vbox = QVBoxLayout()
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
        # 'is_connected' takes values True, False
        worker_exists = status.get("worker_environment_exists", False)
        running_item_uid = status.get("running_item_uid", None)
        queue_stop_pending = status.get("queue_stop_pending", False)
        queue_autostart_enabled = status.get("queue_autostart_enabled", False)

        self._status_queue_autostart_enabled = queue_autostart_enabled

        s = "RUNNING" if running_item_uid else "STOPPED"
        self._lb_queue_state.setText(s)

        if queue_autostart_enabled:
            pb_queue_start_enabled = False
        else:
            pb_queue_start_enabled = (
                is_connected and worker_exists and not bool(running_item_uid)
            )

        self._pb_queue_start.setEnabled(pb_queue_start_enabled)
        self._pb_queue_exec_one.setEnabled(pb_queue_start_enabled)

        self._pb_queue_stop.setEnabled(
            is_connected and worker_exists and bool(running_item_uid)
        )
        self._pb_queue_stop.setChecked(queue_stop_pending)

        cb_enabled = is_connected and worker_exists
        cb_checked = cb_enabled and queue_autostart_enabled
        self._cb_queue_autostart.setEnabled(cb_enabled)

        self._cb_queue_autostart.setChecked(Qt.Checked if cb_checked else Qt.Unchecked)

    def _pb_queue_start_clicked(self):
        try:
            self.model.queue_start()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_queue_exec_one_clicked(self):
        try:
            resp = self.model._client.item_remove(pos="front")
            if resp["success"]:
                self.model._client.item_execute(resp["item"])
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_queue_stop_clicked(self):
        try:
            if self._pb_queue_stop.isChecked():
                self.model.queue_stop()
            else:
                self.model.queue_stop_cancel()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _cb_queue_autostart_state_changed(self, state):
        try:
            enable = state == Qt.Checked
            if enable != self._status_queue_autostart_enabled:
                self._status_queue_autostart_enabled = enable
                self.model.queue_autostart(enable=enable)
        except Exception as ex:
            print(f"Exception: {ex}")
