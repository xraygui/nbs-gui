"""Mixin classes for GUI widgets."""


class ModeManagedWidget:
    """Mixin for widgets that can be enabled/disabled based on modes.

    This mixin provides functionality to automatically enable/disable and
    show/hide widgets based on the availability of their associated model
    in the current mode.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        has_model = hasattr(self, "model")
        has_availability = hasattr(self.model, "availability_changed")
        if has_model and has_availability:
            self.register_for_mode_management(self.model)
            self._on_availability_change(self.model.available)

    def register_for_mode_management(self, model):
        """Register this widget for mode management."""
        model.availability_changed.connect(self._on_availability_change)

    def _on_availability_change(self, available):
        """Handle changes in model availability."""
        self.setEnabled(available)
        self.setVisible(available)
