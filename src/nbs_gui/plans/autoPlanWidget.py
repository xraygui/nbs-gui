"""
Auto-plan widget that introspects plan parameters and builds UI automatically.
"""

from nbs_gui.plans.planParam import AutoParamGroup
from nbs_gui.plans.base import PlanWidgetBase
from bluesky_queueserver import construct_parameters
import inspect
from qtpy.QtWidgets import QSizePolicy
from qtpy.QtCore import Slot, Signal
from typing import Union, get_origin, get_args


class AutoPlanWidget(PlanWidgetBase):
    """
    Widget that automatically builds parameter UI based on plan introspection.

    This widget introspects a plan's parameters and creates appropriate
    parameter widgets (spinboxes, combos, text fields, etc.) automatically.
    Can be used standalone or as a parameter generator for meta-plans.
    """

    signal_update_widgets = Signal()

    def __init__(self, model, plan_name, parent=None, title=None):
        super().__init__(model, parent)
        self.plan_name = plan_name
        self.title = title or f"Plan: {plan_name}"
        self.param_group = None
        self.parameters = []
        self.raw_parameters = {}

        # Set size policy to allow expansion
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.load_plan_parameters()
        self.setup_widget()
        self.run_engine_client.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

    @Slot()
    def slot_update_widgets(self):
        if self.run_engine_client.re_manager_connected:
            self.load_plan_parameters()
            self.setup_widget()

    def on_update_widgets(self, event):
        self.signal_update_widgets.emit()

    def load_plan_parameters(self):
        """Load and introspect plan parameters from the model."""

        try:
            # Get plan parameters using the same method as plan editor
            is_connected = bool(self.run_engine_client.re_manager_connected)
            if not is_connected:
                print("Not connected to RE Manager")
                return
            self.raw_parameters = self.run_engine_client.get_allowed_plan_parameters(
                name=self.plan_name
            )
            self.parameters = construct_parameters(
                self.raw_parameters.get("parameters", {})
            )
            # print(f"Plan parameters: {self.parameters}")

        except Exception as e:
            self.parameters = []
            self.raw_parameters = {}
            print(f"Error loading plan parameters for {self.plan_name}: {e}")

    def setup_widget(self):
        """Build parameter widgets based on introspected parameters."""
        # Clear existing parameters by recreating the param group
        if self.param_group:
            self.layout.removeWidget(self.param_group)
            self.param_group.deleteLater()

        self.param_group = AutoParamGroup(self.model, self, title=self.title)
        self.layout.addWidget(self.param_group)
        self.param_group.editingFinished.connect(self.check_plan_ready)

        # Create AutoParamGroup parameters from parameter objects
        for p in self.parameters:
            param_config = self._convert_parameter_to_config(p)
            self.param_group.add_auto_param(p.name, param_config, p.name)

    def _convert_parameter_to_config(self, param):
        """Convert inspect.Parameter to AutoParamGroup configuration."""
        # Default to no type specification (will use LineEditParam for strings)
        config = {}
        param_types = []

        # Try to infer type from annotation or default
        if param.annotation != inspect.Parameter.empty:
            origin = get_origin(param.annotation)
            if origin is not None:
                # This is a generic type - check if it's a Union
                if origin == Union:
                    # Extract all non-None types from Union
                    args = get_args(param.annotation)
                    param_types = [arg for arg in args if arg is not type(None)]
                else:
                    # Handle other generic types if needed
                    pass
            else:
                # Direct type annotation (not a generic)
                param_types = [param.annotation]

            # Set config based on param_types (check most restrictive first)
            if float in param_types:
                config = {"type": "spinbox", "args": {"value_type": float}}
            elif int in param_types:
                config = {"type": "spinbox", "args": {"value_type": int}}
            elif bool in param_types:
                config = {"type": "boolean"}
            # For str annotation, don't specify type - will use LineEditParam by default

        # Add default value if available
        if param.default != inspect.Parameter.empty:
            if "args" in config:
                config["args"]["default"] = param.default
            else:
                config["default"] = param.default

        return config

    def get_params(self):
        """Get the current parameter values."""
        if self.param_group:
            return self.param_group.get_params()
        return {}

    def get_required_height(self):
        """
        Calculate the height needed based on number and types of parameters.

        Returns
        -------
        int
            Required height in pixels: 30px base + variable height per parameter
        """
        if not self.param_group:
            return 30  # Minimum height for empty widget

        # Count parameters and calculate height based on types
        total_height = 30  # base height

        for p in self.parameters:
            param_config = self._convert_parameter_to_config(p)
            param_type = param_config.get("type", "")

            # AutoPlanWidget strings have no param_type, so they use LineEditParam (30px)
            # Only explicit "text" or "multiline_text" types use TextEditParam (150px)
            if param_type in ["text", "multiline_text"]:
                total_height += 150  # TextEditParam needs more space
            else:
                total_height += (
                    30  # Single-line inputs (LineEditParam, spinbox, combo, etc.)
                )

        return total_height

    def _check_ready(self):
        """Check if the plan is ready to be submitted."""
        if not self.param_group:
            return False

        # Check if all required parameters are set
        params = self.get_params()
        return bool(params)

    def reset(self):
        """Reset all parameters to default values."""
        if self.param_group:
            self.param_group.reset()
        self.check_plan_ready()

    def create_plan_items(self):
        """Create plan items for standalone use."""
        from bluesky_queueserver_api import BPlan

        params = self.get_params()
        if not params:
            return []

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

        item = BPlan(self.plan_name, *args, **kwargs)
        return [item]
