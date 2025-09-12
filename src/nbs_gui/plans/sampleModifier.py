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
    QGroupBox,
    QFormLayout,
)

from qtpy.QtCore import Signal, Qt
from .planParam import LineEditParam, SpinBoxParam
from ..widgets.qt_custom import ScrollingComboBox


class SampleDialog(QDialog):
    def __init__(self, samples={}, parent=None):
        super().__init__(parent)

        self.list_widget = QListWidget()
        self.sample_keys = sorted(list(samples.keys()))

        for k in self.sample_keys:
            s = samples[k]
            item = QListWidgetItem(f"Sample {k}: {s.get('name', '')}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, k)
            self.list_widget.addItem(item)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        # Add Check All and Uncheck All buttons
        self.check_all_button = QPushButton("Check All Samples")
        self.uncheck_all_button = QPushButton("Uncheck All Samples")
        self.check_all_button.clicked.connect(self.check_all_samples)
        self.uncheck_all_button.clicked.connect(self.uncheck_all_samples)

        # Layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.check_all_button)
        button_layout.addWidget(self.uncheck_all_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def check_all_samples(self):
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.Checked)

    def uncheck_all_samples(self):
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.Unchecked)

    def get_checked_samples(self):
        checked_samples = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                checked_samples.append(item.data(Qt.UserRole))
        return checked_samples


def create_position_widget(pos):
    # print(f"SampleComboParam: Creating widget for {pos}")
    if pos == "x":
        help_text = "Horizontal offset from sample center"
        minimum = -20
        maximum = 20
        default = 0
    if pos == "y":
        help_text = "Vertical offset from sample center"
        default = 0
        minimum = -100
        maximum = 100
    if pos == "r":
        help_text = "Sample angle with respect to beam, from 0=grazing to 90=normal"
        default = 45
        minimum = 0
        maximum = 90
    widget = LineEditParam(
        pos,
        value_type=float,
        label="Sample " + pos + " Offset",
        # default=default,
        help_text=help_text,
        # minimum=minimum,
        # maximum=maximum,
    )

    # widget = LineEditParam(pos, float, "Sample " + pos)
    label = QLabel(widget.label_text)
    return widget, label


class NoSampleDummy(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.input_widget = QLabel("Stay in Place")
        # self.input_widget.setStyleSheet("QWidget { background-color: red; }")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.input_widget)


class SampleComboParam(QWidget):
    editingFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.samples = {}
        # Use ScrollingComboBox instead of QComboBox
        self.input_widget = ScrollingComboBox(max_visible_items=10)
        self.input_widget.addItem("Select Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        # print(f"SampleComboParam: Adding {len(self.samples)} samples to QComboBox")
        self.input_widget.addItems(self.samples.keys())
        # print("SampleComboParam: Connecting currentIndexChanged signal")
        self.input_widget.currentIndexChanged.connect(
            lambda x: self.editingFinished.emit()
        )
        # print("SampleComboParam: Setting up layout")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.addWidget(self.input_widget)
        # print("SampleComboParam: Creating position widgets")
        self.position_layout = QFormLayout()
        self.position_layout.setSpacing(2)  # Adjust spacing as needed
        self.position_layout.setContentsMargins(2, 2, 2, 2)  # Adjust margins as needed
        self.position_widgets = []
        for pos in ["x", "y", "r"]:
            widget, label = create_position_widget(pos)
            self.position_layout.addRow(label, widget)
            # widget.setStyleSheet("QWidget { background-color: red; }")
            self.position_widgets.append(widget)
        self.layout.addLayout(self.position_layout)
        # print(
        #     f"SampleComboParam: Created {len(self.position_widgets)} position widgets"
        # )
        # print("SampleComboParam: Initialization complete")

    def update_samples(self, sample_dict):
        self.samples = sample_dict
        self.input_widget.clear()
        self.input_widget.addItem("Select Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        self.input_widget.addItems(
            [
                "Sample {}: {}".format(k, v["name"])
                for k, v in sorted(self.samples.items())
            ]
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


class MultiSampleParam(QWidget):
    editingFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # print("MultiSampleParam")
        self.samples = {}
        self.checked_samples = []
        self.dialog_accepted = False
        self.input_widget = QPushButton("Sample Select (0 selected)")
        self.input_widget.clicked.connect(self.create_sample_dialog)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.addWidget(self.input_widget)

        # print("SampleComboParam: Creating position widgets")
        self.position_layout = QFormLayout()
        self.position_layout.setSpacing(2)  # Adjust spacing as needed
        self.position_layout.setContentsMargins(2, 2, 2, 2)  # Adjust margins as needed
        self.position_widgets = []
        for pos in ["x", "y", "r"]:
            widget, label = create_position_widget(pos)
            self.position_layout.addRow(label, widget)
            # widget.setStyleSheet("QWidget { background-color: red; }")
            self.position_widgets.append(widget)
        self.layout.addLayout(self.position_layout)
        # print("MultiSampleParam Done")

    def update_samples(self, sample_dict):
        self.samples = sample_dict

    def create_sample_dialog(self):
        """
        Create a sample dialog and store the checked samples when the dialog is accepted.
        """
        dialog = SampleDialog(self.samples)
        if dialog.exec():
            self.checked_samples = dialog.get_checked_samples()
            if self.checked_samples:
                self.dialog_accepted = True
                self.update_button_text()
                self.editingFinished.emit()
            else:
                self.dialog_accepted = False
                self.update_button_text()

    def update_button_text(self):
        """Update the button text to show number of selected samples"""
        num_selected = len(self.checked_samples)
        self.input_widget.setText(f"Sample Select ({num_selected} selected)")

    def check_ready(self):
        return self.dialog_accepted

    def get_params(self):
        positions = {}
        for widget in self.position_widgets:
            positions.update(widget.get_params())
        return [
            {"sample": sample, "sample_position": positions}
            for sample in self.checked_samples
        ]

    def reset(self):
        self.checked_samples = []
        self.update_button_text()


class SampleSelectWidget(QGroupBox):
    signal_update_samples = Signal(object)
    editingFinished = Signal()
    is_ready = Signal(bool)

    def __init__(self, model, parent=None):
        super().__init__("Sample Selection", parent=parent)
        print("Initializing Sample Select")

        # Create the main layout
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top

        self.setLayout(self.layout)

        self.user_status = model.user_status
        self.samples = self.user_status.get_redis_dict("GLOBAL_SAMPLES")
        self.samples.changed.connect(self.update_samples)

        self.sample_label = QLabel("Sample Select Option")

        self.sample_option = QComboBox()
        # print("Creating stacked widget")
        self.sample_selection = QStackedWidget()
        # self.sample_selection.setAlignment(Qt.AlignTop)
        self.no_sample = NoSampleDummy(self)

        # print("Creating Single Sample Combo")
        self.one_sample = SampleComboParam(self)
        self.one_sample.editingFinished.connect(self.editingFinished.emit)
        # print("Creating Multi Sample Combo")
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
        self.sample_selection.currentChanged.connect(
            lambda x: self.editingFinished.emit()
        )
        h = QHBoxLayout()
        h.addWidget(self.sample_label)
        h.addWidget(self.sample_option)
        self.layout.addLayout(h)
        self.layout.addWidget(self.sample_selection)
        self.update_samples()
        # print("Sample Select Initialized")

    def clear_sample_selection(self, *args):
        self.dialog_accepted = False
        self.checked_samples = []

    def update_samples(self):
        # print("Got Sample Update")
        self.one_sample.update_samples(self.samples)
        self.multi_sample.update_samples(self.samples)

    def get_params(self):
        if self.sample_option.currentText() == "No Sample":
            params = [{}]
        elif self.sample_option.currentText() == "One Sample":
            params = self.one_sample.get_params()
        elif self.sample_option.currentText() == "Multiple Samples":
            params = self.multi_sample.get_params()
        return {"samples": params}

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
