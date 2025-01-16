"""Mixin class for widgets that need to respond to beamline mode changes."""

from qtpy.QtCore import Signal


class ModeManagedWidget:
    """Mixin class for widgets that can be locked/unlocked based on beamline mode.

    This mixin provides the interface and basic functionality for widgets that
    need to respond to beamline mode changes. Widgets using this mixin should:
    1. Call super().__init__() in their __init__ method
    2. Override update_locked_appearance() to customize visual feedback
    3. Override update_mode_specific_behavior() if needed
    """

    # Signal emitted when widget lock state changes
    lock_state_changed = Signal(bool)

    def __init__(self, *args, **kwargs):
        """Initialize the mixin state."""
        self._locked = False
        self._current_mode = None

    def set_mode_locked(self, locked: bool):
        """Set whether this widget is locked in the current mode.

        Parameters
        ----------
        locked : bool
            If True, widget will be disabled and show locked state
        """
        if self._locked == locked:
            return

        self._locked = locked
        self.setEnabled(not locked)
        self.update_locked_appearance()
        self.lock_state_changed.emit(locked)

    def on_mode_change(self, mode: str):
        """Handle beamline mode changes.

        Parameters
        ----------
        mode : str
            New beamline mode
        """
        self._current_mode = mode
        self.update_mode_specific_behavior()

    def update_locked_appearance(self):
        """Update widget appearance based on locked state.

        Override this method to customize how the widget appears when locked.
        Default implementation only changes enabled state.
        """
        pass

    def update_mode_specific_behavior(self):
        """Update widget behavior based on current mode.

        Override this method to implement mode-specific behavior changes.
        Default implementation does nothing.
        """
        pass

    @property
    def is_locked(self) -> bool:
        """Whether the widget is currently locked."""
        return self._locked

    @property
    def current_mode(self) -> str:
        """Current beamline mode."""
        return self._current_mode
