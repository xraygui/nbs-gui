from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QSizePolicy,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Signal, Qt
from bluesky_widgets.qt.run_engine_client import QtRePlanQueue
from bluesky_queueserver_api import BPlan
from .base import BasicPlanWidget


class MovePlanWidget(BasicPlanWidget):
    signal_update_motors = Signal(object)
    modifiersAllowed = []

    def __init__(self, model, parent=None):
        print("Initializing Move")
        super().__init__(
            model, parent, {"Move": "mv", "Relative Move": "mvr"}, position=float
        )
        self.signal_update_motors.connect(self.update_motors)
        self.user_status.register_signal(
            "MOTORS_DESCRIPTIONS", self.signal_update_motors
        )
        self.display_name = "Movement"
        print("Move Initialized")
        # Create and add the move related widgets here

    def setup_widget(self):
        print("About to initialize super setup_widget")
        super().setup_widget()
        print("Creating move modifier")
        self.motors = {}
        self.user_status.register_signal(
            "MOTORS_DESCRIPTIONS", self.signal_update_motors
        )
        self.create_move_modifier()

    def update_motors(self, plan_dict):
        inverted_dict = {}
        for key, value in plan_dict.items():
            if value != "":
                inverted_dict[value] = key
            else:
                inverted_dict[key] = key
        self.motors = inverted_dict
        self.motor_selection.clear()
        self.motor_selection.addItems(self.motors.keys())
        print(plan_dict)

    def create_move_modifier(self):
        self.motor_selection = QComboBox(self)
        self.motor_selection.addItems(self.motors.keys())
        h = QHBoxLayout()
        h.addWidget(QLabel("Motor to Move"))
        h.addWidget(self.motor_selection)
        self.basePlanLayout.addLayout(h)

    def submit_plan(self):
        motor_text = self.motor_selection.currentText()
        motor = self.motors[motor_text]
        params = self.get_params()
        item = BPlan(self.current_plan, motor, params["position"])
        self.run_engine_client.queue_item_add(item=item)
