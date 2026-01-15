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

        # Main layout
        vbox = QVBoxLayout()

        # Add beamline monitoring section
        print("Adding beamline monitoring section...")
        self._add_beamline_monitoring(vbox)
        vbox.addWidget(HLine())

        # Add energy control if available
        if hasattr(self.beamline, "energy") and self.beamline.energy is not None:
            print("Adding energy control...")
            vbox.addWidget(AutoControl(self.beamline.energy))
            print("Energy control added")

        # Add motor controls and sample selection
        print("Adding motor and sample controls...")
        self._add_motor_and_sample_controls(vbox)
        print("Motor and sample controls added")

        vbox.addStretch()
        self.setLayout(vbox)
        print("Monitor Tab initialization complete")

    def _add_beamline_monitoring(self, layout):
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

        if beamBox.count() > 0:
            layout.addLayout(beamBox)

    def _add_motor_and_sample_controls(self, layout):
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

        if hbox.count() > 0:
            layout.addLayout(hbox)

    def teardown(self):
        """
        Release resources before tab reload.

        Returns
        -------
        None
        """
        return None
