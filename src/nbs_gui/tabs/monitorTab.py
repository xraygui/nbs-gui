from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..views.status import StatusBox, BLController
from ..widgets.utils import HLine
from ..views.views import AutoControlBox, AutoMonitorBox, AutoControl, AutoControlCombo
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
        print("Beamline detectors box")
        vbox1.addWidget(AutoMonitorBox(beamline.detectors, "Detectors", model, "h"))
        print("Beamline detectors box added")
        if hasattr(beamline, "vacuum"):
            print("Beamline vacuum box")
            vbox1.addWidget(AutoMonitorBox(beamline.vacuum, "Vacuum", model, "h"))
            print("Beamline vacuum box added")
        beamBox.addLayout(vbox1)

        vbox.addLayout(beamBox)
        vbox.addWidget(HLine())
        print("Beamline energy box")
        vbox.addWidget(AutoControl(beamline.energy, model))
        print("Beamline energy box added")

        print("Beamline motors box")
        hbox = QHBoxLayout()
        hbox.addWidget(
            AutoControlCombo(
                beamline.motors | beamline.manipulators | beamline.mirrors,
                "Choose a Motor",
                model,
            )
        )
        print("Beamline motors box added")
        """
        hbox.addWidget(
            RealManipulatorControl(
                beamline.primary_sampleholder, model, orientation="v"
            )
        )
        print("Added manipulator Monitor")
        """
        print("Beamline sample select box")
        hbox.addWidget(SampleSelectWidget(model))
        print("Beamline sample select box added")
        print("Beamline status box")
        hbox.addWidget(
            StatusBox(user_status, "Selected Information", "GLOBAL_SELECTED")
        )
        print("Beamline status box added")
        vbox.addLayout(hbox)

        vbox.addStretch()
        self.setLayout(vbox)
        print("Finished Initializing MonitorTab")
