from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QDialog,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
)

from qtpy.QtCore import Signal, Qt
from .base import BaseParam, LineEditParam


class SampleDialog(QDialog):
    def __init__(self, samples={}, parent=None):
        super().__init__(parent)

        self.list_widget = QListWidget()
        self.sample_keys = list(samples.keys())

        for k, s in samples.items():
            item = QListWidgetItem(f"Sample {k}: {s}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def get_checked_samples(self):
        checked_samples = []
        for index in range(self.list_widget.count()):
            if self.list_widget.item(index).checkState() == Qt.Checked:
                checked_samples.append(self.sample_keys[index])
        return checked_samples


class SampleComboParam(BaseParam):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        print("SampleComboParam")
        self.samples = {}
        self.input_widget = QComboBox()
        self.input_widget.addItem("Select Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        self.input_widget.addItems(self.samples.keys())
        self.input_widget.currentIndexChanged.connect(self.editingFinished.emit)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.input_widget)
        self.position_layout = QHBoxLayout(self)
        self.position_widgets = []
        for pos in ["x", "y", "r"]:
            widget = LineEditParam(pos, float, "Sample " + pos)
            self.position_layout.addWidget(widget)
            self.position_widgets.append(widget)
        self.layout.addLayout(self.position_layout)
        print("SampleComboParam Done")

    def update_samples(self, sample_dict):
        self.samples = sample_dict
        self.input_widget.clear()
        self.input_widget.addItem("Select Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        self.input_widget.addItems(
            ["Sample {}: {}".format(k, v["name"]) for k, v in self.samples.items()]
        )

    def check_ready(self):
        return self.input_widget.currentIndex() != 0

    def get_params(self):
        sampletext = self.input_widget.currentText()
        sample_id = sampletext.split(":")[0][7:]
        positions = {}
        for widget in self.position_widgets:
            positions.update(widget.get_params())
        return [{"sample": sample_id, "sample_position": positions}]

    def reset(self):
        self.input_widget.setCurrentIndex(0)


class MultiSampleParam(BaseParam):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        print("MultiSampleParam")
        self.samples = {}
        self.checked_samples = []
        self.dialog_accepted = False
        self.input_widget = QPushButton("Sample Select")
        self.input_widget.clicked.connect(self.create_sample_dialog)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.input_widget)
        print("MultiSampleParam Done")

    def update_samples(self, sample_dict):
        self.samples = sample_dict

    def create_sample_dialog(self):
        """
        Create a sample dialog and store the checked samples when the dialog is accepted.
        """
        dialog = SampleDialog(self.samples)
        if dialog.exec():
            self.checked_samples = dialog.get_checked_samples()
            if self.checked_samples is not []:
                self.dialog_accepted = True
                self.editingFinished.emit()
            else:
                self.dialog_accepted = False

    def check_ready(self):
        return self.dialog_accepted

    def get_params(self):
        return [{"sample": sample} for sample in self.checked_samples]

    def reset(self):
        self.checked_samples = []


class SampleSelectWidget(BaseParam):
    signal_update_samples = Signal(object)
    is_ready = Signal(bool)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        print("Initializing Sample Select")
        self.layout = QHBoxLayout(self)
        self.user_status = model.user_status
        self.signal_update_samples.connect(self.update_samples)
        self.user_status.register_signal("GLOBAL_SAMPLES", self.signal_update_samples)
        self.samples = {}

        self.sample_label = QLabel("Move to Sample")
        self.sample_option = QComboBox()
        self.sample_selection = QStackedWidget()

        self.no_sample = QLabel("(Stay in Place)")
        self.one_sample = SampleComboParam(self)
        self.one_sample.editingFinished.connect(self.editingFinished.emit)
        self.multi_sample = MultiSampleParam(self)
        self.multi_sample.editingFinished.connect(self.editingFinished.emit)

        self.sample_option.addItems(["No Sample", "One Sample", "Multiple Samples"])

        self.sample_selection.addWidget(self.no_sample)
        self.sample_selection.addWidget(self.one_sample)
        self.sample_selection.addWidget(self.multi_sample)

        self.sample_option.currentIndexChanged.connect(
            self.sample_selection.setCurrentIndex
        )
        self.sample_option.currentIndexChanged.connect(self.clear_sample_selection)
        self.sample_selection.currentChanged.connect(self.editingFinished.emit)
        self.layout.addWidget(self.sample_label)
        self.layout.addWidget(self.sample_option)
        self.layout.addWidget(self.sample_selection)
        print("Sample Select Initialized")

    def clear_sample_selection(self, *args):
        self.dialog_accepted = False
        self.checked_samples = []

    def update_samples(self, sample_dict):
        print("Got Sample Update")
        self.samples = sample_dict
        self.one_sample.update_samples(sample_dict)
        self.multi_sample.update_samples(sample_dict)

    def get_params(self):
        if self.sample_option.currentText() == "No Sample":
            return [{}]
        elif self.sample_option.currentText() == "One Sample":
            return self.one_sample.get_params()
        elif self.sample_option.currentText() == "Multiple Samples":
            return self.multi_sample.get_params()

    def emit_ready(self):
        ready_status = self.check_ready()
        self.is_ready.emit(ready_status)

    def check_ready(self):
        """
        Check if all selections have been made and return True if they have.
        """
        if self.sample_option.currentText() == "No Sample":
            return True
        elif self.sample_option.currentText() == "One Sample":
            return self.one_sample.check_ready()
        elif self.sample_option.currentText() == "Multiple Samples":
            return self.multi_sample.check_ready()
        else:
            return False

    def reset(self):
        self.one_sample.reset()
        self.multi_sample.reset()
