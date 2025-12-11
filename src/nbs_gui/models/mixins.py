"""Mixin classes for GUI models."""

from qtpy.QtCore import Signal


class ModeManagedModel:
    """Mixin for device models that can be enabled/disabled.

    This mixin provides a simple availability state that views can use
    to determine if the device should be controllable.
    """

    # Signal emitted when availability changes
    availability_changed = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_available = True

    def set_available(self, available):
        """Set model availability state.

        Parameters
        ----------
        available : bool
            Whether model should be available
        """
        if available != self._is_available:
            self._is_available = available
            self.availability_changed.emit(available)

    @property
    def is_available(self):
        """Whether model is currently available."""
        return self._is_available

    @property
    def available(self):
        """Alias for is_available."""
        return self._is_available
