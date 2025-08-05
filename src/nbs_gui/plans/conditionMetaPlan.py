"""
Condition-based meta-plan widget for repeating plan sequences.
"""

from qtpy.QtWidgets import QVBoxLayout, QGroupBox, QStackedWidget, QLabel
from qtpy.QtCore import Qt
from bluesky_queueserver_api import BPlan
from nbs_gui.plans.planParam import DynamicComboParam
from nbs_gui.plans.autoPlanWidget import AutoPlanWidget
from .metaPlanBase import MetaPlanBase


class ConditionParam(DynamicComboParam):
    """Parameter widget for selecting conditions from the condition list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conditions = {}

    def update_options(self, conditions):
        """Update the dropdown with available conditions."""
        current_text = self.input_widget.currentText()
        self.conditions = conditions
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)

        # Add conditions to dropdown
        for condition in conditions:
            self.input_widget.addItem(str(condition))

        # Restore previous selection if possible
        index = self.input_widget.findText(current_text)
        self.input_widget.setCurrentIndex(index if index >= 0 else 0)

    def get_params(self):
        """Get the selected condition parameter."""
        if self.input_widget.currentIndex() != 0:
            condition = self.input_widget.currentText()
            return {"condition": condition}
        return {}


class ConditionMetaPlan(MetaPlanBase):
    """
    Meta-plan widget for repeating plan sequences while a condition is true.

    This widget creates a repeat_plan_sequence_while_condition plan that runs
    a sequence of plans repeatedly until a condition plan returns False.
    """

    display_name = "Repeat Plan Sequence (While Condition)"
    plan_name = "repeat_plan_sequence_while_condition"

    def setup_plan_ui(self):
        """Set up the condition-specific UI elements."""
        # Create parameters group
        params_group = QGroupBox("Condition Parameters")
        params_layout = QVBoxLayout()

        # Condition plan selection dropdown
        self.condition_param = ConditionParam(
            "condition", "Select Condition", "Select a condition", parent=self
        )
        self.condition_param.editingFinished.connect(self.check_plan_ready)
        params_layout.addWidget(self.condition_param)

        # Register signal for condition updates
        self.user_status.register_signal(
            "CONDITION_LIST", self.condition_param.signal_update_options
        )

        # Create stacked widget for condition parameters
        self.condition_params_stack = QStackedWidget()
        self.condition_params_stack.setMinimumHeight(30)  # Start with minimal height

        # Add a placeholder widget
        placeholder = QLabel("Select a condition to configure its parameters")
        placeholder.setAlignment(Qt.AlignCenter)
        self.condition_params_stack.addWidget(placeholder)

        params_layout.addWidget(self.condition_params_stack)

        # Connect condition selection to parameter widget updates
        self.condition_param.editingFinished.connect(self._update_condition_params)

        params_group.setLayout(params_layout)

        # Insert the parameters group at the top of the layout
        self.layout.insertWidget(0, params_group)
        print("[ConditionMetaPlan] Done setting up condition-specific UI elements")

    def _update_condition_params(self):
        """Update the condition parameter widgets based on selected condition."""
        condition_params = self.condition_param.get_params()
        condition = condition_params.get("condition", "")

        if not condition:
            # No condition selected, show placeholder with minimal height
            self.condition_params_stack.setCurrentIndex(0)
            self.condition_params_stack.setMinimumHeight(30)
            return

        # Check if we already have a widget for this condition
        for i in range(1, self.condition_params_stack.count()):
            widget = self.condition_params_stack.widget(i)
            if hasattr(widget, "plan_name") and widget.plan_name == condition:
                self.condition_params_stack.setCurrentIndex(i)
                # Set height based on the widget's requirements
                required_height = widget.get_required_height()
                self.condition_params_stack.setMinimumHeight(required_height)
                return

        # Create new AutoPlanWidget for this condition
        condition_widget = AutoPlanWidget(
            self.model, condition, self, title=f"Condition: {condition}"
        )
        # Connect parameter changes to our check_plan_ready method
        condition_widget.plan_ready.connect(self.check_plan_ready)

        self.condition_params_stack.addWidget(condition_widget)
        self.condition_params_stack.setCurrentWidget(condition_widget)

        # Set height based on the widget's requirements
        required_height = condition_widget.get_required_height()
        self.condition_params_stack.setMinimumHeight(required_height)

    def check_plan_parameters(self):
        """Check if the condition parameters are ready."""
        if not hasattr(self, "condition_param"):
            return False

        # Check if condition is selected
        if not self.condition_param.check_ready():
            return False

        # Check if condition parameters are ready
        current_widget = self.condition_params_stack.currentWidget()
        if hasattr(current_widget, "_check_ready"):
            return current_widget._check_ready()

        return True

    def _get_condition_args_and_kwargs(self):
        """Get condition args and kwargs from the AutoPlanWidget."""
        current_widget = self.condition_params_stack.currentWidget()

        if hasattr(current_widget, "get_params"):
            params = current_widget.get_params()

            # Extract args and kwargs from params
            args = []
            kwargs = {}

            for key, value in params.items():
                if key == "args" and isinstance(value, str):
                    # Parse comma-separated args string
                    args = [arg.strip() for arg in value.split(",") if arg.strip()]
                elif key == "kwargs" and isinstance(value, str):
                    # Parse comma-separated kwargs string
                    for pair in value.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            kwargs[k.strip()] = v.strip()
                elif key not in ("args", "kwargs"):
                    # Regular parameter
                    kwargs[key] = value

            return args, kwargs

        return [], {}

    def create_plan_items(self):
        """Create the condition meta-plan BPlan item."""
        if not self.staged_plans:
            raise ValueError("No plans selected for meta-plan")

        # Extract plan data
        plans, plan_args_list, plan_kwargs_list = self._extract_plan_data()

        # Get condition parameters
        condition_params = self.condition_param.get_params()
        condition = condition_params.get("condition", "")

        # Get condition args and kwargs from AutoPlanWidget
        condition_args, condition_kwargs = self._get_condition_args_and_kwargs()

        # Create the BPlan
        kwargs = {
            "plans": plans,
            "plan_args_list": plan_args_list,
            "plan_kwargs_list": plan_kwargs_list,
            "condition": condition,
            "condition_args": condition_args,
            "condition_kwargs": condition_kwargs,
        }

        item = BPlan(self.plan_name, **kwargs)
        return [item]

    def reset_plan_parameters(self):
        """Reset the condition parameters."""
        if hasattr(self, "condition_param"):
            self.condition_param.reset()
        if hasattr(self, "condition_params_stack"):
            current_widget = self.condition_params_stack.currentWidget()
            if hasattr(current_widget, "reset"):
                current_widget.reset()


class UntilConditionMetaPlan(ConditionMetaPlan):
    """
    Meta-plan widget for repeating plan sequences until a condition is true.

    This widget creates a repeat_plan_sequence_until_condition plan that runs
    a sequence of plans repeatedly until a condition plan returns True.
    """

    display_name = "Repeat Plan Sequence (Until Condition)"
    plan_name = "repeat_plan_sequence_until_condition"
