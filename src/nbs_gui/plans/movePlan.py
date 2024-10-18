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
from .base import BasicPlanWidget, MotorParam


class MovePlanWidget(BasicPlanWidget):
    modifiersAllowed = []

    def __init__(self, model, parent=None):
        print("Initializing Move")
        super().__init__(
            model,
            parent,
            {"Move": "mv", "Relative Move": "mvr"},
            motor={
                "type": "motor",
                "label": "Motor to Move",
            },
            position=float,
        )
        self.display_name = "Movement"
        print("Move Initialized")

    def submit_plan(self):
        params = self.get_params()
        item = BPlan(self.current_plan, params["motor"], params["position"])
        self.run_engine_client.queue_item_add(item=item)
