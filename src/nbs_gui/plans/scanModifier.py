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
from .base import ParamGroup, SpinBoxParam, LineEditParam


class ScanModifierParam(ParamGroup):
    def __init__(self, parent=None):
        super().__init__(parent, "Scan Setup")
        self.add_param(SpinBoxParam("repeat", "Repeat", minimum=1, default=1))
        self.add_param(LineEditParam("comment", str, "Comment"))
        self.add_param(LineEditParam("group_name", str, "Group Name"))

    def check_ready(self):
        # All parameters optional, so return True
        return True


class ReferenceComboParam(QWidget):
    editingFinished = Signal()
    signal_update_samples = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.key = "eref_sample"
        self.label_text = "Energy Reference"
        self.user_status = model.user_status

        print("RefComboParam: Initializing")
        self.samples = {}
        print("RefComboParam: Creating QComboBox")
        self.input_widget = QComboBox()
        self.input_widget.addItem("Select Reference Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        print(f"RefComboParam: Adding {len(self.samples)} samples to QComboBox")
        self.input_widget.addItems(self.samples.keys())
        print("RefComboParam: Connecting currentIndexChanged signal")
        self.input_widget.currentIndexChanged.connect(self.editingFinished.emit)
        print("RefComboParam: Setting up layout")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.input_widget)

        print("RefComboParam: Initialization complete")
        self.user_status.register_signal(
            "REFERENCE_SAMPLES", self.signal_update_samples
        )
        self.signal_update_samples.connect(self.update_samples)

    def update_samples(self, sample_dict):
        self.samples = sample_dict
        self.input_widget.clear()
        self.input_widget.addItem("Select Reference Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        self.input_widget.addItems(
            ["Sample {}: {}".format(k, v["name"]) for k, v in self.samples.items()]
        )

    def check_ready(self):
        return self.input_widget.currentIndex() != 0

    def get_params(self):
        sampletext = self.input_widget.currentText()
        sample_id = sampletext.split(":")[0][7:]
        return {"eref_sample": sample_id}

    def reset(self):
        self.input_widget.setCurrentIndex(0)


class BeamlineModifierParam(ParamGroup):
    def __init__(self, model, parent=None):
        super().__init__(parent, "Beamline Setup")

        self.add_param(LineEditParam("exit_slit", float, "Exit Slit"))
        self.add_param(LineEditParam("polarization", float, "Polarization"))
        self.add_param(LineEditParam("energy", float, "Energy"))
        self.add_param(ReferenceComboParam(model))

    def check_ready(self):
        # All parameters optional, so return True
        return True
