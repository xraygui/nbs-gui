"""
Condition-based meta-plan widget for repeating plan sequences.
"""

from qtpy.QtWidgets import QVBoxLayout, QGroupBox
from bluesky_queueserver_api import BPlan
from nbs_gui.plans.planParam import LineEditParam
from .metaPlanBase import MetaPlanBase


class ConditionMetaPlan(MetaPlanBase):
    """
    Meta-plan widget for repeating plan sequences while a condition is true.

    This widget creates a repeat_plan_sequence_while_condition plan that runs
    a sequence of plans repeatedly until a condition plan returns False.
    """

    display_name = "Repeat Plan Sequence (Condition)"

    def setup_plan_ui(self):
        """Set up the condition-specific UI elements."""
        # Create parameters group
        params_group = QGroupBox("Condition Parameters")
        params_layout = QVBoxLayout()

        # Condition plan name
        self.condition_param = LineEditParam("condition", str, "Condition Plan Name")
        self.condition_param.editingFinished.connect(self.check_plan_ready)
        params_layout.addWidget(self.condition_param)

        # Condition args (simplified as comma-separated string)
        self.condition_args_param = LineEditParam(
            "condition_args", str, "Condition Args (comma-separated)"
        )
        self.condition_args_param.editingFinished.connect(self.check_plan_ready)
        params_layout.addWidget(self.condition_args_param)

        # Condition kwargs (simplified as comma-separated key=value)
        self.condition_kwargs_param = LineEditParam(
            "condition_kwargs", str, "Condition Kwargs (key=value, comma-separated)"
        )
        self.condition_kwargs_param.editingFinished.connect(self.check_plan_ready)
        params_layout.addWidget(self.condition_kwargs_param)

        params_group.setLayout(params_layout)

        # Insert the parameters group at the top of the layout
        self.layout.insertWidget(0, params_group)
        print("[ConditionMetaPlan] Done setting up condition-specific UI elements")

    def check_plan_parameters(self):
        """Check if the condition parameters are ready."""
        if not hasattr(self, "condition_param"):
            return False
        return self.condition_param.check_ready()

    def _parse_condition_args(self, args_str):
        """Parse condition args string into list."""
        if not args_str.strip():
            return []
        return [arg.strip() for arg in args_str.split(",")]

    def _parse_condition_kwargs(self, kwargs_str):
        """Parse condition kwargs string into dict."""
        if not kwargs_str.strip():
            return {}
        kwargs = {}
        for pair in kwargs_str.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                kwargs[key.strip()] = value.strip()
        return kwargs

    def create_plan_items(self):
        """Create the condition meta-plan BPlan item."""
        if not self.staged_plans:
            raise ValueError("No plans selected for meta-plan")

        # Extract plan data
        plans, plan_args_list, plan_kwargs_list = self._extract_plan_data()

        # Get condition parameters
        condition_params = self.condition_param.get_params()
        condition = condition_params.get("condition", "")

        # Parse condition args and kwargs
        condition_args_params = self.condition_args_param.get_params()
        args_str = condition_args_params.get("condition_args", "")
        condition_args = self._parse_condition_args(args_str)

        condition_kwargs_params = self.condition_kwargs_param.get_params()
        kwargs_str = condition_kwargs_params.get("condition_kwargs", "")
        condition_kwargs = self._parse_condition_kwargs(kwargs_str)

        # Create the BPlan
        kwargs = {
            "plans": plans,
            "plan_args_list": plan_args_list,
            "plan_kwargs_list": plan_kwargs_list,
            "condition": condition,
            "condition_args": condition_args,
            "condition_kwargs": condition_kwargs,
        }

        item = BPlan("repeat_plan_sequence_while_condition", **kwargs)
        return [item]

    def reset_plan_parameters(self):
        """Reset the condition parameters."""
        if hasattr(self, "condition_param"):
            self.condition_param.reset()
        if hasattr(self, "condition_args_param"):
            self.condition_args_param.reset()
        if hasattr(self, "condition_kwargs_param"):
            self.condition_kwargs_param.reset()
