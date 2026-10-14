from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..views.status import StatusBox, SampleStatusBox
from ..widgets.utils import HLine
from ..views.views import (
    AutoControlBox,
    AutoMonitorBox,
    AutoControl,
    AutoControlCombo,
)
from ..widgets.sampleSelect import SampleSelectWidget


class MonitorTab(QWidget):
    name = "Beamline Status"
    reloadable = True

    def __init__(self, model, *args, **kwargs):
        print("Initializing Monitor Tab...")
        super().__init__(*args, **kwargs)
        self.user_status = model.user_status
        self.beamline = model.beamline
        self.model = model
        self.monitor_layout = None
        self.energy_layout = None
        self.control_layout = None

        # Main layout
        self.main_layout = QVBoxLayout()

        # Add beamline monitoring section
        print("Adding beamline monitoring section...")
        self.monitor_layout = self._create_beamline_monitoring()
        if self.monitor_layout.count() > 0:
            self.main_layout.addLayout(self.monitor_layout)
            self.main_layout.addWidget(HLine())

        # Add energy control if available
        self.energy_layout = self._create_energy_control()
        if self.energy_layout.count() > 0:
            self.main_layout.addLayout(self.energy_layout)
            self.main_layout.addWidget(HLine())


        # Add motor controls and sample selection
        print("Adding motor and sample controls...")
        self.control_layout = self._create_motor_and_sample_controls()
        if self.control_layout.count() > 0:
            self.main_layout.addLayout(self.control_layout)

        print("Motor and sample controls added")

        self.main_layout.addStretch()
        self.setLayout(self.main_layout)
        print("Monitor Tab initialization complete")

    def _create_beamline_monitoring(self):
        beamBox = QHBoxLayout()

        # Add signals monitoring if available
        signals = getattr(self.beamline, "signals", {})
        if signals:
            print("Adding ring signals monitor...")
            beamBox.addWidget(
                AutoMonitorBox(signals, "Ring Signals", orientation="v")
            )
            print("Ring signals monitor added")

        # Add shutters control if available
        shutters = getattr(self.beamline, "shutters", {})
        if shutters:
            print("Adding shutters control...")
            beamBox.addWidget(AutoControlBox(shutters, "Shutters"))
            print("Shutters control added")

        # Add detectors and vacuum monitoring
        vbox1 = QVBoxLayout()

        detectors = getattr(self.beamline, "detectors", {})
        if detectors:
            print("Adding detectors monitor...")
            vbox1.addWidget(
                AutoMonitorBox(detectors, "Detectors", orientation="h")
            )
            print("Detectors monitor added")

        vacuum = getattr(self.beamline, "vacuum", {})
        if vacuum:
            print("Adding vacuum monitor...")
            vbox1.addWidget(
                AutoMonitorBox(vacuum, "Vacuum", orientation="h")
            )
            print("Vacuum monitor added")

        if vbox1.count() > 0:
            beamBox.addLayout(vbox1)
        return beamBox

    def _create_energy_control(self):
        energy_layout = QHBoxLayout()
        if hasattr(self.beamline, "energy") and self.beamline.energy is not None:
            print("Adding energy control...")
            energy_layout.addWidget(AutoControl(self.beamline.energy))
            print("Energy control added")
        return energy_layout

    def _create_motor_and_sample_controls(self):
        hbox = QHBoxLayout()

        # Combine available motor-like devices
        motor_devices = {}

        motors = getattr(self.beamline, "motors", {})
        if motors:
            print("Adding motor devices...")
            motor_devices.update(motors)

        manipulators = getattr(self.beamline, "manipulators", {})
        if manipulators:
            print("Adding manipulator devices...")
            motor_devices.update(manipulators)

        mirrors = getattr(self.beamline, "mirrors", {})
        if mirrors:
            print("Adding mirror devices...")
            motor_devices.update(mirrors)

        # Add motor control if any motors are available
        if motor_devices:
            print("Creating motor control widget...")
            hbox.addWidget(AutoControlCombo(motor_devices, "Choose a Motor"))
            print("Motor control widget added")

        # Add sample selection if available
        has_sampleholder = (
            hasattr(self.beamline, "primary_sampleholder")
            and self.beamline.primary_sampleholder is not None
        )
        if has_sampleholder:
            print("Adding sample selection widgets...")
            hbox.addWidget(SampleSelectWidget(self.model))
            hbox.addWidget(SampleStatusBox(self.user_status, "Selected Sample"))
            print("Sample selection widgets added")

        return hbox

    def teardown(self):
        """
        Release resources before tab reload.

        Returns
        -------
        None
        """
        return None
