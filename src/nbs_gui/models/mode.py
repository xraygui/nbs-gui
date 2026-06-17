"""Model for beamline mode control."""

from qtpy.QtCore import Signal

from nbs_gui.views.mode import ModeControl, RedisModeControl
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
    default_controller = ModeControl
    default_monitor = ModeControl
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


    @property
    def current_mode(self):
        """Current beamline mode."""
        return self._current_mode

    @property
    def available_modes(self):
        """List of available mode names."""
        return self.enum_strs or [self.current_mode]


class RedisModeModel(PVModel):
    """Mode model for Redis-backed active mode lists.

    Parameters
    ----------
    name : str
        Name of the mode control.
    obj : RedisModeDevice
        Redis-backed mode device with an ``active_modes`` signal.
    group : str
        Group this model belongs to.
    long_name : str
        Display name for the mode control.
    """

    default_controller = RedisModeControl
    default_monitor = RedisModeControl
    valueChanged = Signal(object)
    mode_changed = Signal(object)
    active_modes_changed = Signal(object)
    available_modes_changed = Signal(object)
    hidden_modes = ("default",)

    def __init__(self, name, obj, group, long_name,  **kwargs):
        self.mode_device = obj
        self._active_modes = []
        self._available_modes = []
        self.available_sub_key = None
        super().__init__(name, obj.active_modes, group, long_name, **kwargs)
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
                self._on_value_changed(initial)
            self._initialize_available_modes()
        except Exception as e:
            print(f"{self.name} redis mode init failed: {e}")

    def _initialize_available_modes(self):
        available_modes_signal = getattr(self.mode_device, "available_modes", None)
        if available_modes_signal is None:
            self._set_available_modes(self._active_modes)
            return
        try:
            self.available_sub_key = available_modes_signal.subscribe(
                self._available_modes_changed,
                run=False,
            )
            initial = available_modes_signal.get()
        except Exception as e:
            print(f"Error reading available redis modes for {self.name}: {e}")
            initial = None
        if initial is not None:
            self._set_available_modes(initial)
        else:
            self._set_available_modes(self._active_modes)

    def _on_value_changed(self, value):
        modes = self._set_active_modes(value)
        self.mode_changed.emit(modes)
        self.active_modes_changed.emit(modes)

    def _value_changed(self, value, **kwargs):
        modes = self._coerce_modes(value)
        if modes != self._active_modes:
            self._active_modes = modes
            self.valueChanged.emit(modes)

    def _available_modes_changed(self, value, **kwargs):
        self._set_available_modes(value)

    def _set_active_modes(self, value):
        modes = self._coerce_modes(value)
        self._active_modes = modes
        if not self._available_modes:
            self._set_available_modes(modes)
        return modes

    def _set_available_modes(self, value):
        modes = self._coerce_modes(value)
        if not modes:
            modes = list(self._active_modes)
        if modes != self._available_modes:
            self._available_modes = modes
            self.available_modes_changed.emit(modes)
        return modes

    def set_mode(self, mode):
        self.activate_mode(mode)

    def activate_mode(self, mode):
        try:
            modes = list(self._active_modes)
            if mode not in modes:
                modes.append(mode)
            self.obj.put(modes)
        except Exception as e:
            print(f"Error activating redis mode for {self.name}: {e}")

    def deactivate_mode(self, mode):
        try:
            modes = [active_mode for active_mode in self._active_modes if active_mode != mode]
            self.obj.put(modes)
        except Exception as e:
            print(f"Error deactivating redis mode for {self.name}: {e}")

    def set_available_modes(self, modes):
        available_modes_signal = getattr(self.mode_device, "available_modes", None)
        if available_modes_signal is None:
            self._set_available_modes(modes)
            return
        try:
            available_modes_signal.put(modes)
        except Exception as e:
            print(f"Error setting redis available modes for {self.name}: {e}")
            self._set_available_modes(modes)

    def _coerce_modes(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        try:
            return list(value)
        except TypeError:
            return [value]

    @property
    def current_mode(self):
        return ", ".join(self._active_modes)

    @property
    def active_modes(self):
        return list(self._active_modes)

    @property
    def available_modes(self):
        return self._visible_modes(self._available_modes or self._active_modes)

    @property
    def inactive_modes(self):
        return [
            mode for mode in self.available_modes
            if mode not in self._active_modes
        ]

    def _visible_modes(self, modes):
        return [
            mode for mode in modes
            if mode not in self.hidden_modes
        ]
