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
from bluesky_queueserver_api import BPlan
from .base import DynamicComboParam
from .nbsPlan import NBSPlanWidget


class XASPlanWidget(NBSPlanWidget):
    signal_update_xas = Signal(object)

    def __init__(self, model, parent=None):
        print("Initializing XAS")
        self.display_name = "XAS"
        super().__init__(
            model,
            parent,
            "dummy",
        )
        self.signal_update_xas.connect(self.update_xas)
        self.user_status.register_signal("XAS_PLANS", self.signal_update_xas)
        print("XAS Initialized")
        # Add all the XAS related methods and widgets here

    def setup_widget(self):
        super().setup_widget()
        self.xas_plans = {}
        self.edge_selection = DynamicComboParam(
            "edge", "Edge", "Select Edge", parent=self
        )
        self.scan_widget.add_param(self.edge_selection)
        self.user_status.register_signal("XAS_PLANS", self.signal_update_xas)
        self.user_status.register_signal(
            "XAS_PLANS", self.edge_selection.signal_update_options
        )

    def check_plan_ready(self):
        """
        Check if all selections have been made and emit the plan_ready signal if they have.
        """
        print("Checking XAS Plan")
        if self.sample_select.check_ready() and self.edge_selection.check_ready():
            print("XAS Ready to Submit")
            self.plan_ready.emit(True)
        else:
            print("XAS not ready")
            self.plan_ready.emit(False)

    def update_xas(self, plan_dict):
        self.xas_plans = plan_dict
        self.edge_selection.signal_update_options.emit(self.xas_plans.keys())
        self.widget_updated.emit()

    def submit_plan(self):
        params = self.get_params()
        edge = params.pop("edge")
        samples = params.pop("samples")

        for s in samples:
            item = BPlan(self.xas_plans[edge], **s, **params)
            self.run_engine_client.queue_item_add(item=item)

    def reset(self):
        super().reset()
        self.sample_widget.reset()
