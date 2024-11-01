from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Signal, Qt
from typing import Any
from .planParam import AutoParamGroup


class PlanWidgetBase(QWidget):
    widget_updated = Signal()
    plan_ready = Signal(bool)
    editingFinished = Signal()

    def __init__(self, model, parent=None, plans="", **kwargs):
        """
        If plan is a string, it will be used as the item name for submission
        If it is a dict, it will be used to create a drop-down menu
        """
        print("Initializing PlanWidgetBase")
        super().__init__(parent)
        self.model = model
        self.plans = plans
        if isinstance(plans, str):
            self.current_plan = plans

        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.layout = QVBoxLayout(self)
        self.basePlanLayout = QVBoxLayout()
        self.layout.addLayout(self.basePlanLayout)
        self.editingFinished.connect(self.check_plan_ready)

        self.params = []
        self.setup_widget()
        print("Done PlanWidgetBase Initialized")

    def current_plan_changed(self, idx=None):
        # print("Current Plan Changed Run")
        plan_display = self.plan_combo_list.currentText()
        # print(f"Plan display {plan_display}")
        if plan_display in self.plans:
            self.current_plan = self.plans[plan_display]
        else:
            self.current_plan = None
        # print(f"{self.current_plan}")

    def setup_widget(self):
        # print("PlanWidgetBase setup_widget")
        if isinstance(self.plans, dict):
            self.plan_combo_list = QComboBox()
            for display_key in self.plans.keys():
                self.plan_combo_list.addItem(display_key)
            self.plan_combo_list.currentIndexChanged.connect(self.current_plan_changed)
            h = QHBoxLayout()
            h.addWidget(QLabel("Plan Subtype"))
            h.addWidget(self.plan_combo_list)
            self.basePlanLayout.addLayout(h)
            self.current_plan_changed()

        # print("PlanWidgetBase setup_widget finished")

    def get_params(self):
        """
        Get parameters from the input widgets.

        Returns
        -------
        dict
            A dictionary of parameters.
        """
        # print("Getting PlanWidgetBase Params")
        params = {}
        for widget in self.params:
            params.update(widget.get_params())
        return params

    def check_plan_ready(self):
        # print("Checking PlanWidgetBase ready")
        checks = [widget.check_ready() for widget in self.params]
        if all(checks):
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def reset(self):
        for widget in self.params:
            widget.reset()

    def submit_plan(self, item):
        """
        Submit a plan item to the run engine client.

        Parameters
        ----------
        item : BPlan
            The plan item to be submitted.

        Returns
        -------
        bool
            True if the submission was successful, False otherwise.
        """
        try:
            self.run_engine_client.queue_item_add(item=item)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Submission Error",
                f"Failed to submit plan: {str(e)}",
                QMessageBox.Ok,
            )
            return False

    def create_plan_items(self):
        """
        Create and return a list of plan items to be submitted.
        This method should be implemented by child classes.

        Returns
        -------
        list
            A list of BPlan items to be submitted.
        """
        raise NotImplementedError("This method should be implemented by child classes.")

    def submit_all_plans(self):
        """
        Create and submit all plan items.
        """
        plan_items = self.create_plan_items()
        for item in plan_items:
            if not self.submit_plan(item):
                break  # Stop submitting if an error occurs


class BasicPlanWidget(PlanWidgetBase):
    def __init__(self, model, parent=None, plans="", **kwargs):
        """
        If plan is a string, it will be used as the item name for submission
        If it is a dict, it will be used to create a drop-down menu
        """
        self.initial_kwargs = kwargs
        super().__init__(model, parent, plans)

    def setup_widget(self):
        # print("BasicPlanWidget setup_widget")
        super().setup_widget()
        self.planWidget = AutoParamGroup(self.model, self, **self.initial_kwargs)
        self.planWidget.editingFinished.connect(self.editingFinished)
        # print("Updating input widgets")
        self.params.append(self.planWidget)
        # print("Adding widget to layout")
        self.layout.addWidget(self.planWidget)
        # print("BasicPlanWidget setup_widget finished")
