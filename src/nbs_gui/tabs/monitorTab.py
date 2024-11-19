from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..widgets.status import StatusBox, BLController
from ..widgets.utils import HLine
from ..widgets.manipulator_monitor import (
    RealManipulatorControl,
    PseudoManipulatorControl,
)
from ..widgets.views import AutoControlBox, AutoMonitorBox, AutoControl, AutoControlCombo
from ..widgets.sampleSelect import SampleSelectWidget


class MonitorTab(QWidget):
    name = "Beamline Status"

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        run_engine = model.run_engine
        user_status = model.user_status
        beamline = model.beamline
        vbox = QVBoxLayout()

        beamBox = QHBoxLayout()
        print("Creating Beamline signals box")

        beamBox.addWidget(
            AutoMonitorBox(beamline.signals, "Ring Signals", model, orientation="v")
        )
        print("Beamline signals box added")

        print("Beamline shutters box")
        beamBox.addWidget(AutoControlBox(beamline.shutters, "Shutters", model))
        print("Beamline shutters box added")
        

        vbox1 = QVBoxLayout()
        vbox1.addWidget(AutoMonitorBox(beamline.detectors, "Detectors", model, "h"))
        if hasattr(beamline, "vacuum"):
            vbox1.addWidget(AutoMonitorBox(beamline.vacuum, "Vacuum", model, "h"))
        beamBox.addLayout(vbox1)
        
        vbox.addLayout(beamBox)
        vbox.addWidget(HLine())
        vbox.addWidget(AutoControl(beamline.energy, model))
        
        print("Added detectors Monitor")

        hbox = QHBoxLayout()
        hbox.addWidget(
            AutoControlCombo(
                beamline.motors | beamline.manipulators | beamline.mirrors,
                "Choose a Motor",
                model,
            )
        )
        """
        hbox.addWidget(
            RealManipulatorControl(
                beamline.primary_sampleholder, model, orientation="v"
            )
        )
        print("Added manipulator Monitor")
        """
        hbox.addWidget(SampleSelectWidget(model))
        hbox.addWidget(
            StatusBox(user_status, "Selected Information", "GLOBAL_SELECTED")
        )
        print("Added StatusBox")
        vbox.addLayout(hbox)


        vbox.addStretch()
        self.setLayout(vbox)
        print("Finished Initializing MonitorTab")
