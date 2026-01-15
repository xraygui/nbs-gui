"""Model for beamline mode control."""

from qtpy.QtCore import Signal
from .base import EnumModel, PVModel, initialize_with_retry, requires_connection


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
        self._initialize()

    @initialize_with_retry
    def _initialize(self):
        if not super()._initialize():
            return False
        try:
            self.sub_key = self.obj.subscribe(self._mode_changed)
            return True
        except Exception as e:
            print(f"Error subscribing to mode changes for {self.name}: {e}")
            return False

    def _mode_changed(self, value, **kwargs):
        """Handle mode changes from PV."""
        try:
            if isinstance(value, (int, float)):
                # Convert enum index to string if possible
                if self.enum_strs and 0 <= value < len(self.enum_strs):
                    mode = self.enum_strs[int(value)]
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

    @requires_connection
    def set_mode(self, mode):
        """Set the beamline mode.

        Parameters
        ----------
        mode : str or int
            Mode to set. Can be mode name or enum index.
        """
        try:
            if isinstance(mode, str):
                if mode in self.enum_strs:
                    # Convert mode name to enum index
                    mode = self.enum_strs.index(mode)
                elif mode.startswith("Mode_"):
                    # Convert Mode_N back to integer
                    try:
                        mode = int(mode.split("_")[1])
                    except (IndexError, ValueError):
                        raise ValueError(f"Invalid mode format: {mode}")
                else:
                    raise ValueError(f"Invalid mode: {mode}")

            # For Redis-backed devices, prefer put; for enum PVs, set also works
            if hasattr(self.obj, "put"):
                self.obj.put(mode)
            else:
                self.obj.set(mode).wait()
        except Exception as e:
            print(f"Error setting mode for {self.name}: {e}")

    @property
    def current_mode(self):
        """Current beamline mode."""
        return self._current_mode

    @property
    def available_modes(self):
        """List of available mode names."""
        return self.enum_strs or [self.current_mode]


class RedisModeModel(PVModel):
    """Mode model for Redis-backed mode signals (free-form strings)."""

    mode_changed = Signal(str)

    def __init__(self, name, obj, group, long_name,  **kwargs):
        super().__init__(name, obj.mode, group, long_name, **kwargs)
        self._current_mode = "Unknown"
        self._initialize_redis_mode()

    def _initialize_redis_mode(self):
        try:
            self.valueChanged.connect(self._on_value_changed)
            initial = None
            try:
                initial = self.obj.get()
            except Exception as e:
                print(f"Error reading initial redis mode for {self.name}: {e}")
            if initial is not None:
                self._on_value_changed(str(initial))
        except Exception as e:
            print(f"{self.name} redis mode init failed: {e}")

    def _on_value_changed(self, value):
        mode = str(value)
        self._current_mode = mode
        self.mode_changed.emit(mode)

    def set_mode(self, mode):
        try:
            if hasattr(self.obj, "put"):
                self.obj.put(mode)
            else:
                self.obj.set(mode).wait()
        except Exception as e:
            print(f"Error setting redis mode for {self.name}: {e}")

    @property
    def current_mode(self):
        return self._current_mode

    @property
    def available_modes(self):
        return [self._current_mode]
