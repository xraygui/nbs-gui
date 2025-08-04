"""
Auto-plan widget that introspects plan parameters and builds UI automatically.
"""

from nbs_gui.plans.planParam import AutoParamGroup
from nbs_gui.plans.base import PlanWidgetBase
from bluesky_queueserver import construct_parameters
import inspect


class AutoPlanWidget(PlanWidgetBase):
    """
    Widget that automatically builds parameter UI based on plan introspection.

    This widget introspects a plan's parameters and creates appropriate
    parameter widgets (spinboxes, combos, text fields, etc.) automatically.
    Can be used standalone or as a parameter generator for meta-plans.
    """

    def __init__(self, model, plan_name, parent=None, title=None):
        super().__init__(model, parent)
        self.plan_name = plan_name
        self.title = title or f"Plan: {plan_name}"
        self.param_group = None
        self.plan_parameters = None

        self.setup_ui()
        self.load_plan_parameters()

    def setup_ui(self):
        """Set up the basic UI structure using existing layout."""
        # Create parameter group using existing layout
        self.param_group = AutoParamGroup(self.model, self, title=self.title)
        self.layout.addWidget(self.param_group)

        # Connect parameter changes to plan ready signal
        self.param_group.editingFinished.connect(self.check_plan_ready)

    def load_plan_parameters(self):
        """Load and introspect plan parameters from the model."""
        if not self.plan_name:
            return

        try:
            # Get plan parameters using the same method as plan editor
            self.plan_parameters = self.model.run_engine.get_allowed_plan_parameters(
                name=self.plan_name
            )

            if self.plan_parameters and "parameters" in self.plan_parameters:
                self._build_parameter_widgets()
            else:
                # Fallback: create a simple text parameter
                self._build_fallback_widget()

        except Exception as e:
            print(f"Error loading plan parameters for {self.plan_name}: {e}")
            self._build_fallback_widget()

    def _build_parameter_widgets(self):
        """Build parameter widgets based on introspected parameters."""
        if not self.param_group:
            return

        # Clear existing parameters by recreating the param group
        self.layout.removeWidget(self.param_group)
        self.param_group.deleteLater()

        self.param_group = AutoParamGroup(self.model, self, title=self.title)
        self.layout.addWidget(self.param_group)
        self.param_group.editingFinished.connect(self.check_plan_ready)

        # Use the same parameter construction as plan editor
        parameters = self.plan_parameters.get("parameters", {})

        # Use construct_parameters to get proper parameter objects
        param_objects = construct_parameters(parameters)

        # Create AutoParamGroup parameters from parameter objects
        for p in param_objects:
            param_config = self._convert_parameter_to_config(p)
            self.param_group.auto_param(p.name, param_config, p.name)

    def _convert_parameter_to_config(self, param):
        """Convert inspect.Parameter to AutoParamGroup configuration."""
        # Default to text input
        config = {"type": "text"}

        # Try to infer type from annotation or default
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == int:
                config = {"type": "spinbox", "args": {"value_type": int}}
            elif param.annotation == float:
                config = {"type": "spinbox", "args": {"value_type": float}}
            elif param.annotation == bool:
                config = {"type": "boolean"}

        # Add default value if available
        if param.default != inspect.Parameter.empty:
            if "args" in config:
                config["args"]["default"] = param.default
            else:
                config["default"] = param.default

        return config

    def _build_fallback_widget(self):
        """Build a fallback widget when parameter introspection fails."""
        if not self.param_group:
            return

        # Clear existing parameters by recreating the param group
        self.layout.removeWidget(self.param_group)
        self.param_group.deleteLater()

        self.param_group = AutoParamGroup(self.model, self, title=self.title)
        self.layout.addWidget(self.param_group)
        self.param_group.editingFinished.connect(self.check_plan_ready)

        # Create a simple text parameter for manual entry
        self.param_group.auto_param(
            "args",
            {"type": "text", "help_text": "Plan arguments (comma-separated)"},
            "Arguments",
        )
        self.param_group.auto_param(
            "kwargs",
            {
                "type": "text",
                "help_text": "Plan keyword arguments (key=value, comma-separated)",
            },
            "Keyword Arguments",
        )

    def get_params(self):
        """Get the current parameter values."""
        if self.param_group:
            return self.param_group.get_params()
        return {}

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

    def update_plan_name(self, plan_name):
        """Update the plan name and reload parameters."""
        self.plan_name = plan_name
        self.title = f"Plan: {plan_name}"
        if self.param_group:
            self.param_group.setTitle(self.title)
        self.load_plan_parameters()
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
