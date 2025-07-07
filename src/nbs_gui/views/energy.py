from qtpy.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from .motor import MotorMonitor, MotorControl
from .manipulator_monitor import ManipulatorMonitor, PseudoManipulatorControl

from bluesky_queueserver_api import BPlan
from nbs_gui.settings import get_top_level_model


class EnergyMonitor(QGroupBox):
    """
    Display an Energy Model that has energy, gap, and phase
    """

    def __init__(self, energy, *args, parent_model=None, orientation=None, **kwargs):
        super().__init__("Energy Monitor", *args, **kwargs)
        hbox = QHBoxLayout()
        vbox1 = QVBoxLayout()
        for m in energy.energy.pseudo_axes_models:
            vbox1.addWidget(MotorMonitor(m))
        vbox1.addWidget(
            MotorMonitor(get_top_level_model().beamline.motors["Exit_Slit"])
        )
        vbox1.addWidget(MotorMonitor(energy.grating_motor))
        vbox2 = QVBoxLayout()
        for m in energy.energy.real_axes_models:
            vbox2.addWidget(MotorMonitor(m))
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        self.setLayout(hbox)


class EnergyControl(QGroupBox):
    def __init__(self, energy, *args, parent_model=None, orientation=None, **kwargs):
        super().__init__("Energy Control", *args, **kwargs)

        print(energy)
        self.REClientModel = get_top_level_model().run_engine
        print("Creating Energy Control Vbox")
        vbox = QVBoxLayout()
        print("Creating Energy Motor")
        for m in energy.energy.pseudo_axes_models:
            vbox.addWidget(MotorControl(m))
        # vbox.addWidget(PseudoManipulatorControl(energy.energy, parent_model))
        print("Creating Exit Slit")
        vbox.addWidget(MotorControl(get_top_level_model().beamline.motors["Exit_Slit"]))
        print("Making hbox")
        hbox = QHBoxLayout()
        hbox.addWidget(MotorMonitor(energy.grating_motor))
        print("Making ComboBox")
        cb = QComboBox()
        self.cb = cb
        cb.addItem("250 l/mm", 2)
        cb.addItem("1200 l/mm", 9)
        self.button = QPushButton("Change Grating")
        self.button.clicked.connect(self.change_grating)
        hbox.addWidget(cb)
        hbox.addWidget(self.button)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def change_grating(self):
        enum = self.cb.currentData()
        print(enum)
        if self.confirm_dialog():
            if enum == 9:
                plan = BPlan("change_grating", 1200)
            else:
                plan = BPlan("change_grating", 250)
            self.REClientModel._client.item_execute(plan)

    def confirm_dialog(self):
        """
        Show the confirmation dialog with the proper message in case
        ```showConfirmMessage``` is True.

        Returns
        -------
        bool
            True if the message was confirmed or if ```showCofirmMessage```
            is False.
        """

        confirm_message = "Are you sure you want to change gratings?"
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)

        msg.setText(confirm_message)

        # Force "Yes" button to be on the right (as on macOS) to follow common design practice
        msg.setStyleSheet("button-layout: 1")  # MacLayout

        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.No:
            return False
        return True
