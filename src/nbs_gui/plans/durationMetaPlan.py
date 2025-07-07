"""
Duration-based meta-plan widget for repeating plan sequences.
"""

from qtpy.QtWidgets import QVBoxLayout, QGroupBox
from bluesky_queueserver_api import BPlan
from nbs_gui.plans.planParam import SpinBoxParam
from .metaPlanBase import MetaPlanBase


class DurationMetaPlan(MetaPlanBase):
    """
    Meta-plan widget for repeating plan sequences for a specified duration.

    This widget creates a repeat_plan_sequence_for_duration plan that runs
    a sequence of plans repeatedly until the specified duration is reached.
    """

    display_name = "Repeat Plan Sequence (Duration)"

    def setup_plan_ui(self):
        """Set up the duration-specific UI elements."""
        print("[DurationMetaPlan] Setting up duration-specific UI elements")
        # Create parameters group
        params_group = QGroupBox("Duration Parameters")
        params_layout = QVBoxLayout()

        # Duration parameter
        self.duration_param = SpinBoxParam(
            "duration",
            "Duration (seconds)",
            value_type=float,
            minimum=1.0,
            maximum=86400.0,  # 24 hours
            default=60.0,
        )
        print("[DurationMetaPlan] Adding duration parameter to layout")
        self.duration_param.editingFinished.connect(self.check_plan_ready)
        params_layout.addWidget(self.duration_param)

        params_group.setLayout(params_layout)
        print("[DurationMetaPlan] Adding parameters group to layout")
        # Insert the parameters group at the top of the layout
        self.layout.insertWidget(0, params_group)
        print("[DurationMetaPlan] Done setting up duration-specific UI elements")

    def check_plan_parameters(self):
        """Check if the duration parameter is ready."""
        if not hasattr(self, "duration_param"):
            return False
        return self.duration_param.check_ready()

    def create_plan_items(self):
        """Create the duration meta-plan BPlan item."""
        if not self.staged_plans:
            raise ValueError("No plans selected for meta-plan")

        # Extract plan data
        plans, plan_args_list, plan_kwargs_list = self._extract_plan_data()

        # Get duration parameter
        duration_params = self.duration_param.get_params()
        duration = duration_params.get("duration", 60.0)

        # Create the BPlan
        kwargs = {
            "plans": plans,
            "plan_args_list": plan_args_list,
            "plan_kwargs_list": plan_kwargs_list,
            "duration": duration,
        }

        item = BPlan("repeat_plan_sequence_for_duration", **kwargs)
        return [item]

    def reset_plan_parameters(self):
        """Reset the duration parameter."""
        if hasattr(self, "duration_param"):
            self.duration_param.reset()
