from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
)

from qtpy.QtCore import Signal, Qt
from .planParam import ParamGroup, SpinBoxParam, LineEditParam, TextEditParam
from nbs_gui.settings import SETTINGS
from importlib.metadata import entry_points


class DefaultScanModifierParam(ParamGroup):
    def __init__(self, model, parent=None):
        super().__init__(parent, "Scan Setup")
        self.add_param(SpinBoxParam("repeat", "Repeat", minimum=1, default=1))
        self.add_param(
            LineEditParam(
                "group_name",
                str,
                "Group Name",
                help_text="A group name which can be used to provide a search tag to associate multiple scans",
            )
        )
        self.add_param(
            TextEditParam(
                "comment",
                "Comment",
                help_text="Any comment or useful text to store with the scan",
            )
        )

    def check_ready(self):
        # All parameters optional, so return True
        return True


# Check settings for custom scan modifier
try:
    scan_modifier_name = (
        SETTINGS.gui_config.get("gui", {}).get("plans", {}).get("scan_modifier", None)
    )
except Exception as e:
    print(f"Error getting scan modifier name: {e}")
    scan_modifier_name = None

# Default to DefaultScanModifierParam
ScanModifierParam = DefaultScanModifierParam

# If a specific scan modifier is configured, try to load it
if scan_modifier_name:
    try:
        scan_modifier_eps = entry_points(group="nbs_gui.plans.scanModifier")
        for ep in scan_modifier_eps:
            if ep.name == scan_modifier_name:
                ScanModifierParam = ep.load()
                print(f"Loaded custom scan modifier: {scan_modifier_name}")
                break
        else:
            print(
                f"Warning: Configured scan modifier '{scan_modifier_name}' not found in entrypoints"
            )
    except Exception as e:
        print(f"Error loading custom scan modifier '{scan_modifier_name}': {e}")
        print("Falling back to default scan modifier")


class ReferenceComboParam(QWidget):
    editingFinished = Signal()
    signal_update_samples = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.key = "eref_sample"
        self.label_text = "Energy Reference"
        self.help_text = "Select a reference sample on the Multimesh sampleholder"
        self.user_status = model.user_status

        # print("RefComboParam: Initializing")
        self.samples = {}
        # print("RefComboParam: Creating QComboBox")
        self.input_widget = QComboBox()
        self.input_widget.addItem("Select Reference Sample")
        self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        # print(f"RefComboParam: Adding {len(self.samples)} samples to QComboBox")
        self.input_widget.addItems(self.samples.keys())
        # print("RefComboParam: Connecting currentIndexChanged signal")
        self.input_widget.currentIndexChanged.connect(
            lambda x: self.editingFinished.emit()
        )
        # print("RefComboParam: Setting up layout")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)  # Align widgets to the top
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addWidget(self.input_widget)

        # print("RefComboParam: Initialization complete")
        self.signal_update_samples.connect(self.update_samples)
        self.user_status.register_signal(
            "REFERENCE_SAMPLES", self.signal_update_samples
        )

    def update_samples(self, sample_dict):
        self.samples = sample_dict
        self.input_widget.clear()
        self.input_widget.addItem("Auto (default)")
        # self.input_widget.setItemData(0, "", Qt.UserRole - 1)
        self.input_widget.addItems(
            [
                "Sample {}: {}".format(k, v["name"])
                for k, v in sorted(self.samples.items())
            ]
        )

    def check_ready(self):
        return self.input_widget.currentIndex() != 0

    def get_params(self):
        if self.input_widget.currentIndex() == 0:
            return {}
        sampletext = self.input_widget.currentText()
        sample_id = sampletext.split(":")[0][7:]
        return {"eref_sample": sample_id}

    def reset(self):
        self.input_widget.setCurrentIndex(0)


class DefaultBeamlineModifierParam(ParamGroup):
    def __init__(self, model, parent=None):
        super().__init__(parent, "Beamline Setup")

        config = SETTINGS.beamline_config.get("configuration", {})
        if config.get("has_slits", False):
            self.add_param(LineEditParam("eslit", float, "Exit Slit"))
        if config.get("has_polarization", False):
            self.add_param(
                LineEditParam(
                    "polarization",
                    float,
                    "Polarization",
                    "EPU Polarization to set at plan start",
                )
            )
        if config.get("has_motorized_eref", False):
            self.add_param(ReferenceComboParam(model))
        self.add_param(
            LineEditParam("energy", float, "Energy", "Energy to set at plan start")
        )

    def check_ready(self):
        # All parameters optional, so return True
        return True

try:
    beamline_modifier_name = (
        SETTINGS.beamline_config.get("configuration", {}).get("beamline_modifier", None)
    )
except Exception as e:
    print(f"Error getting beamline modifier name: {e}")
    beamline_modifier_name = None

# Default to DefaultBeamlineModifierParam
BeamlineModifierParam = DefaultBeamlineModifierParam

# If a specific scan modifier is configured, try to load it
if beamline_modifier_name:
    try:
        beamline_modifier_eps = entry_points(group="nbs_gui.plans.beamlineModifier")
        for ep in beamline_modifier_eps:
            if ep.name == beamline_modifier_name:
                BeamlineModifierParam = ep.load()
                print(f"Loaded custom beamline modifier: {beamline_modifier_name}")
                break
        else:
            print(
                f"Warning: Configured beamline modifier '{beamline_modifier_name}' not found in entrypoints"
            )
    except Exception as e:
        print(f"Error loading custom beamline modifier '{beamline_modifier_name}': {e}")
        print("Falling back to default beamline modifier")
