from qtpy.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QLabel,
    QDialog,
    QDialogButtonBox,
)
from qtpy.QtCore import Signal, QObject, Slot
from qtpy.QtGui import QDoubleValidator

from bluesky_queueserver_api import BPlan, BFunc


class SampleSelectModel(QObject):
    signal_samples_updated = Signal(object)

    def __init__(self, run_engine, user_status, *args, **kwargs):
        super().__init__()
        self.run_engine = run_engine
        self.samples = user_status.get_redis_dict("GLOBAL_SAMPLES")
        if self.samples is None:
            print("Warning: Redis not configured, sample selection will be empty")
            self.samples = {}
        else:
            self.samples.changed.connect(self.update_samples)
            self.update_samples()

    def update_samples(self):
        """Update samples from Redis data"""
        print(f"SampleSelectModel got samples {self.samples}")
        self.signal_samples_updated.emit(self.samples)

    def select_sample(self, sample, x, y, r, origin):
        plan = BPlan("sample_move", x, y, r, sample, origin=origin)
        return plan


class SampleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Current Position as Sample")
        layout = QVBoxLayout(self)

        # Sample ID
        hbox_id = QHBoxLayout()
        hbox_id.addWidget(QLabel("Sample ID:"))
        self.sample_id_edit = QLineEdit(self)
        hbox_id.addWidget(self.sample_id_edit)
        layout.addLayout(hbox_id)

        # Sample Name
        hbox_name = QHBoxLayout()
        hbox_name.addWidget(QLabel("Sample Name:"))
        self.sample_name_edit = QLineEdit(self)
        hbox_name.addWidget(self.sample_name_edit)
        layout.addLayout(hbox_name)

        # Description
        hbox_desc = QHBoxLayout()
        hbox_desc.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit(self)
        hbox_desc.addWidget(self.description_edit)
        layout.addLayout(hbox_desc)

        # Dialog buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
        )
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)


class SampleSelectWidget(QGroupBox):
    signal_update_widget = Signal(bool, object)

    def __init__(self, model, parent=None, **kwargs):
        super().__init__("Sample Selection", parent=parent)
        self.run_engine = model.run_engine
        self.model = SampleSelectModel(model.run_engine, model.user_status)

        vbox = QVBoxLayout()
        cb = QComboBox()
        self.cb = cb
        self.button = QPushButton("Move Sample")
        self.x = QLineEdit("0")
        self.x.setValidator(QDoubleValidator())
        self.y = QLineEdit("0")
        self.y.setValidator(QDoubleValidator())
        self.r = QLineEdit("45")
        self.r.setValidator(QDoubleValidator())
        self.add_button = QPushButton("Add Current Position as New Sample")
        vbox.addWidget(self.add_button)
        self.add_button.clicked.connect(self.add_current_position)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("x"))
        hbox.addWidget(self.x)
        hbox.addWidget(QLabel("y"))
        hbox.addWidget(self.y)
        hbox.addWidget(QLabel("r"))
        hbox.addWidget(self.r)
        self.button.clicked.connect(self.select_sample)
        vbox.addWidget(self.cb)
        vbox.addLayout(hbox)
        vbox.addWidget(self.button)
        self.setLayout(vbox)
        self.run_engine.events.status_changed.connect(self.slot_update_widgets)
        self.model.signal_samples_updated.connect(self.update_samples)
        self.model.update_samples()
        print("Finish SampleSelectWidget init")

    @Slot(object)
    def slot_update_widgets(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        # 'is_connected' takes values True, False
        worker_exists = status.get("worker_environment_exists", False)
        running_item_uid = status.get("running_item_uid", None)

        enabled = is_connected and worker_exists and not bool(running_item_uid)
        self.button.setEnabled(enabled)

    @Slot(object)
    def update_samples(self, samples):
        print("SampleSelectWidget update_samples called with {samples}")
        self.cb.clear()
        for k, v in sorted(samples.items()):
            self.cb.addItem(f"Sample {k}: {v['name']}", k)

    def select_sample(self):
        sample = self.cb.currentData()
        x = float(self.x.text())
        y = float(self.y.text())
        r = float(self.r.text())
        print((x, y, r))
        plan = BPlan("move_sample", sample, x=x, y=y, r=r)
        self.run_engine._client.item_execute(plan)

    def add_current_position(self):
        dialog = SampleDialog(self)
        if dialog.exec_():
            sample_id = dialog.sample_id_edit.text()
            sample_name = dialog.sample_name_edit.text()
            description = dialog.description_edit.text()
            plan = BFunc(
                "add_current_position_as_sample", sample_name, sample_id, description
            )
            self.run_engine._client.function_execute(plan)
