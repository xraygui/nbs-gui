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
            vbox.addWidget(AutoControl(self.beamline.energy, self.model))
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
        if hasattr(self.beamline, "signals") and self.beamline.signals:
            print("Adding ring signals monitor...")
            beamBox.addWidget(
                AutoMonitorBox(
                    self.beamline.signals, "Ring Signals", self.model, orientation="v"
                )
            )
            print("Ring signals monitor added")

        # Add shutters control if available
        if hasattr(self.beamline, "shutters") and self.beamline.shutters:
            print("Adding shutters control...")
            beamBox.addWidget(
                AutoControlBox(self.beamline.shutters, "Shutters", self.model)
            )
            print("Shutters control added")

        # Add detectors and vacuum monitoring
        vbox1 = QVBoxLayout()

        if hasattr(self.beamline, "detectors") and self.beamline.detectors:
            print("Adding detectors monitor...")
            vbox1.addWidget(
                AutoMonitorBox(self.beamline.detectors, "Detectors", self.model, "h")
            )
            print("Detectors monitor added")

        if hasattr(self.beamline, "vacuum") and self.beamline.vacuum:
            print("Adding vacuum monitor...")
            vbox1.addWidget(
                AutoMonitorBox(self.beamline.vacuum, "Vacuum", self.model, "h")
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

        if hasattr(self.beamline, "motors") and self.beamline.motors:
            print("Adding motor devices...")
            motor_devices.update(self.beamline.motors)

        if hasattr(self.beamline, "manipulators") and self.beamline.manipulators:
            print("Adding manipulator devices...")
            motor_devices.update(self.beamline.manipulators)

        if hasattr(self.beamline, "mirrors") and self.beamline.mirrors:
            print("Adding mirror devices...")
            motor_devices.update(self.beamline.mirrors)

        # Add motor control if any motors are available
        if motor_devices:
            print("Creating motor control widget...")
            hbox.addWidget(
                AutoControlCombo(motor_devices, "Choose a Motor", self.model)
            )
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
