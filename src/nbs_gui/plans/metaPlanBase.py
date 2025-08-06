"""
Base class for meta-plan widgets that run sequences of other plans.
"""

from qtpy.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QLabel,
    QMessageBox,
)
from nbs_gui.plans.base import PlanWidgetBase
import json
from qtpy.QtCore import QMimeData, Qt


class MetaPlanBase(PlanWidgetBase):
    """
    Base class for meta-plan widgets that run sequences of other plans.

    Provides common functionality for:
    - Loading plans from staging queue
    - Managing the list of plans to include
    - Converting plans to the required format for meta-plans
    """

    def __init__(self, model, plan_name, parent=None):
        super().__init__(model, parent)
        self.staged_plans = []  # Plans loaded from staging queue
        self.plan_name = plan_name
        self.setup_common_ui()
        self.setup_plan_ui()

    def setup_common_ui(self):
        """Set up the common UI elements for all meta-plans."""
        # Use the existing layout from PlanWidgetBase instead of creating a new one

        # Staged plans group
        staged_group = QGroupBox("Staged Plans")
        staged_layout = QVBoxLayout()

        # Load from staging button
        self.load_staging_btn = QPushButton("Load Plans from Staging Queue")
        self.load_staging_btn.clicked.connect(self.load_from_staging)
        staged_layout.addWidget(self.load_staging_btn)

        # Staged plans list
        self.staged_plans_list = QListWidget()
        self.staged_plans_list.setMaximumHeight(150)
        staged_layout.addWidget(QLabel("Plans to include in sequence:"))
        staged_layout.addWidget(self.staged_plans_list)

        # Plan management buttons
        plan_buttons = QHBoxLayout()
        self.remove_plan_btn = QPushButton("Remove Selected")
        self.remove_plan_btn.clicked.connect(self.remove_selected_plan)
        self.clear_plans_btn = QPushButton("Clear All")
        self.clear_plans_btn.clicked.connect(self.clear_all_plans)
        plan_buttons.addWidget(self.remove_plan_btn)
        plan_buttons.addWidget(self.clear_plans_btn)
        plan_buttons.addStretch()
        staged_layout.addLayout(plan_buttons)

        staged_group.setLayout(staged_layout)
        self.layout.addWidget(staged_group)

        self.staged_plans_list.setAcceptDrops(True)
        self.staged_plans_list.dragEnterEvent = self._dragEnterEvent
        self.staged_plans_list.dragMoveEvent = self._dragMoveEvent
        self.staged_plans_list.dropEvent = self._dropEvent

    def setup_plan_ui(self):
        """
        Set up the plan-specific UI elements.

        This method should be implemented by subclasses to add their
        specific parameter widgets.
        """
        raise NotImplementedError("Subclasses must implement setup_plan_ui")

    def load_from_staging(self):
        """Load plans from the staging queue."""
        try:
            staged_items = self.model.queue_staging.staged_plans
            if not staged_items:
                QMessageBox.information(
                    self,
                    "No Staged Plans",
                    "No plans are currently in the staging queue.",
                )
                return
            self.staged_plans.clear()
            self.staged_plans_list.clear()
            for item in staged_items:
                self.staged_plans.append(item)
                plan_name = item.get("name", "Unknown Plan")
                plan_args = item.get("args", [])
                plan_kwargs = item.get("kwargs", {})
                display_text = f"{plan_name}"
                if plan_args:
                    display_text += f" args: {plan_args}"
                if plan_kwargs:
                    display_text += f" kwargs: {plan_kwargs}"
                list_item = QListWidgetItem(display_text)
                self.staged_plans_list.addItem(list_item)
            self.check_plan_ready()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load plans from staging: {str(e)}"
            )

    def remove_selected_plan(self):
        """Remove the selected plan from the list."""
        current_row = self.staged_plans_list.currentRow()
        if current_row >= 0:
            self.staged_plans.pop(current_row)
            self.staged_plans_list.takeItem(current_row)
            self.check_plan_ready()

    def clear_all_plans(self):
        """Clear all plans from the list."""
        self.staged_plans.clear()
        self.staged_plans_list.clear()
        self.check_plan_ready()

    def _check_ready(self):
        """Check if the meta-plan is ready for submission."""
        # Must have at least one plan
        if not self.staged_plans:
            return False

        # Check parameter widgets (implemented by subclasses)
        return self.check_plan_parameters()

    def check_plan_parameters(self):
        """
        Check if the plan-specific parameters are ready.

        This method should be implemented by subclasses to check their
        specific parameter widgets.
        """
        return True

    def check_plan_ready(self):
        """Check if the plan is ready and emit signal."""
        ready = self._check_ready()
        self.plan_ready.emit(ready)

    def _extract_plan_data(self):
        """
        Extract plan names, args, and kwargs from staged plans.

        Returns
        -------
        tuple
            (plans, plan_args_list, plan_kwargs_list)
        """
        plans = []
        plan_args_list = []
        plan_kwargs_list = []

        for item in self.staged_plans:
            plans.append(item["name"])
            plan_args_list.append(item.get("args", []))
            plan_kwargs_list.append(item.get("kwargs", {}))

        return plans, plan_args_list, plan_kwargs_list

    def create_plan_items(self):
        """
        Create the meta-plan BPlan item.

        This method should be implemented by subclasses to create their
        specific meta-plan BPlan.
        """
        raise NotImplementedError("Subclasses must implement create_plan_items")

    def submit_meta_plan(self):
        """Submit the meta-plan to the main queue."""
        try:
            plan_items = self.create_plan_items()
            for item in plan_items:
                self.submit_plan(item)
            QMessageBox.information(
                self, "Success", "Meta-plan submitted to queue successfully."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit meta-plan: {str(e)}")

    def stage_meta_plan(self):
        """Stage the meta-plan."""
        try:
            plan_items = self.create_plan_items()
            for item in plan_items:
                self.stage_plan(item)
            QMessageBox.information(self, "Success", "Meta-plan staged successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stage meta-plan: {str(e)}")

    def reset(self):
        """Reset the widget to initial state."""
        self.staged_plans.clear()
        self.staged_plans_list.clear()
        self.reset_plan_parameters()

    def reset_plan_parameters(self):
        """
        Reset the plan-specific parameters.

        This method should be implemented by subclasses to reset their
        specific parameter widgets.
        """
        pass

    def _dragEnterEvent(self, event):
        print("Drag enter event received")
        print(event.mimeData().formats())
        if event.mimeData().hasFormat("application/x-bluesky-plan"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _dragMoveEvent(self, event):
        print("Drag move event received")
        print(event.mimeData().formats())
        if event.mimeData().hasFormat("application/x-bluesky-plan"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _dropEvent(self, event):
        print("Drop event received")
        if event.mimeData().hasFormat("application/x-bluesky-plan"):
            data = event.mimeData().data("application/x-bluesky-plan")
            try:
                plans = json.loads(bytes(data).decode("utf-8"))
                if isinstance(plans, dict):
                    plans = [plans]
                added = False
                for plan in plans:
                    if not isinstance(plan, dict):
                        continue
                    self.staged_plans.append(plan)
                    plan_name = plan.get("name", "Unknown Plan")
                    plan_args = plan.get("args", [])
                    plan_kwargs = plan.get("kwargs", {})
                    display_text = f"{plan_name}"
                    if plan_args:
                        display_text += f" args: {plan_args}"
                    if plan_kwargs:
                        display_text += f" kwargs: {plan_kwargs}"
                    list_item = QListWidgetItem(display_text)
                    self.staged_plans_list.addItem(list_item)
                    added = True
                if added:
                    self.check_plan_ready()
                    event.acceptProposedAction()
                else:
                    event.ignore()
            except Exception:
                event.ignore()
        else:
            print("Drop event ignored")
            print(event.mimeData().formats())
            event.ignore()
