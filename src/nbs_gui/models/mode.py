"""Model for beamline mode control."""

from qtpy.QtCore import Signal
from .base import EnumModel


class ModeModel(EnumModel):
    """Model for beamline mode control.

    This model wraps an EpicsSignal that controls/monitors the beamline mode.
    The PV should be an enum type that defines the available modes.

    Parameters
    ----------
    name : str
        Name of the mode control
    obj : EpicsSignal
        The underlying Ophyd object (mode PV)
    group : str
        Group this model belongs to
    long_name : str
        Display name for the mode control
    mode_info : dict
        Dictionary of mode metadata from config
    """

    # Additional signals specific to mode changes
    mode_changed = Signal(str)  # Emits mode name

    def __init__(self, name, obj, group, long_name, mode_info=None, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.mode_info = mode_info or {}
        self._current_mode = "Unknown"
        self._enum_strs = []

        # Try to get enum strings, but don't fail if not available
        try:
            if hasattr(obj, "enum_strs") and obj.enum_strs is not None:
                self._enum_strs = list(obj.enum_strs)
                print(f"Mode PV {name} has enum strings: {self._enum_strs}")
            else:
                print(f"Warning: Mode PV {name} does not have enum strings")
        except Exception as e:
            print(f"Error getting enum strings for {name}: {e}")

        try:
            self.sub_key = obj.subscribe(self._mode_changed)
        except Exception as e:
            print(f"Error subscribing to mode changes for {name}: {e}")

    def _mode_changed(self, value, **kwargs):
        """Handle mode changes from PV."""
        try:
            if isinstance(value, (int, float)):
                # Convert enum index to string if possible
                if self._enum_strs and 0 <= value < len(self._enum_strs):
                    mode = self._enum_strs[int(value)]
                else:
                    mode = f"Mode_{value}"
            else:
                mode = str(value)

            self._current_mode = mode
            print(f"ModeModel changed to: {mode}")
            self.mode_changed.emit(mode)
            self.valueChanged.emit(mode)
        except Exception as e:
            print(f"Error handling mode change for {self.name}: {e}")

    def set_mode(self, mode):
        """Set the beamline mode.

        Parameters
        ----------
        mode : str or int
            Mode to set. Can be mode name or enum index.
        """
        try:
            if isinstance(mode, str):
                if mode in self._enum_strs:
                    # Convert mode name to enum index
                    mode = self._enum_strs.index(mode)
                elif mode.startswith("Mode_"):
                    # Convert Mode_N back to integer
                    try:
                        mode = int(mode.split("_")[1])
                    except (IndexError, ValueError):
                        raise ValueError(f"Invalid mode format: {mode}")
                else:
                    raise ValueError(f"Invalid mode: {mode}")

            self.obj.put(mode)
        except Exception as e:
            print(f"Error setting mode for {self.name}: {e}")

    @property
    def current_mode(self):
        """Current beamline mode."""
        return self._current_mode

    @property
    def available_modes(self):
        """List of available mode names."""
        return self._enum_strs or [self._current_mode]
