from qtpy.QtCore import Signal, QTimer
import numpy as np

from ..views.gatevalve import GVControl, GVMonitor
from ..views.energy import EnergyControl, EnergyMonitor
from ..views.manipulator_monitor import RealManipulatorControl, RealManipulatorMonitor

from .base import BaseModel, formatFloat, formatInt
from .motors import PVPositionerModel, MotorModel


class EnergyModel:
    default_controller = EnergyControl
    default_monitor = EnergyMonitor

    def __init__(
        self,
        name,
        obj,
        group,
        long_name,
        **kwargs,
    ):
        self.energy = EnergyAxesModel(name, obj, group, name)
        self.grating_motor = PVPositionerModel(
            name=obj.monoen.gratingx.name,
            obj=obj.monoen.gratingx,
            group=group,
            long_name=f"{name} Grating",
        )
        self.name = name
        self.obj = obj
        self.group = group
        self.long_name = long_name
        for key, value in kwargs.items():
            setattr(self, key, value)


class GVModel(BaseModel):
    default_controller = GVControl
    default_monitor = GVMonitor
    gvStatusChanged = Signal(str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.sub_key = self.obj.state.subscribe(self._status_change, run=True)
        timer = QTimer.singleShot(5000, self._check_status)

    def _cleanup(self):
        self.obj.state.unsubscribe(self.sub_key)

    def open(self):
        self.obj.open_nonplan()

    def close(self):
        self.obj.close_nonplan()

    def _check_status(self):
        try:
            status = self.obj.state.get(connection_timeout=0.2, timeout=0.2)
            self._status_change(status)
            QTimer.singleShot(100000, self._check_status)
        except:
            QTimer.singleShot(10000, self._check_status)

    def _status_change(self, value, **kwargs):
        if value == self.obj.openval:
            self.gvStatusChanged.emit("open")
        elif value == self.obj.closeval:
            self.gvStatusChanged.emit("closed")


class ScalarModel(BaseModel):
    valueChanged = Signal(str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        if hasattr(obj, "metadata"):
            self.units = obj.metadata.get("units", None)
            print(f"{name} has units {self.units}")
        else:
            self.units = None
            print(f"{name} has no metadata")

        self.value_type = None
        self._value = "Disconnected"
        self.sub_key = self.obj.target.subscribe(self._value_changed, run=True)
        QTimer.singleShot(5000, self._check_value)

    def _cleanup(self):
        self.obj.target.unsubscribe(self.sub_key)

    def _check_value(self):
        try:
            value = self.obj.target.get(connection_timeout=0.2, timeout=0.2)
            self._value_changed(value)
            self._handle_reconnection()
            QTimer.singleShot(100000, self._check_value)
        except Exception as e:
            self._handle_connection_error(e, "checking value")
            QTimer.singleShot(10000, self._check_value)

    def _value_changed(self, value, **kwargs):
        """Handle value changes, with better type handling."""
        try:
            # Extract value from named tuple if needed
            if hasattr(value, "_fields"):
                if hasattr(value, "user_readback"):
                    value = value.user_readback
                elif hasattr(value, "value"):
                    value = value.value

            # Determine the type if not yet set
            if self.value_type is None:
                if isinstance(value, (float, np.floating)):
                    self.value_type = float
                elif isinstance(value, (int, np.integer)):
                    self.value_type = int
                else:
                    self.value_type = str

            # Format based on type
            if self.value_type is float:
                formatted_value = formatFloat(value)
            elif self.value_type is int:
                formatted_value = formatInt(value)
            else:
                formatted_value = str(value)

            self._value = formatted_value
            self.valueChanged.emit(formatted_value)
        except Exception as e:
            print(f"Error in _value_changed for {self.name}: {e}")
            self._value = str(value)
            self.valueChanged.emit(str(value))

    @property
    def value(self):
        return self._value


class ControlModel(BaseModel):
    controlChange = Signal(str)

    def __init__(self, name, obj, group, long_name, requester=None, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.requester = requester
        self.obj.subscribe(self._control_change)

    def request_control(self, requester=None):
        if requester is None:
            requester = self.requester
        if requester is not None:
            self.obj.set(requester).wait(timeout=10)
        else:
            raise ValueError("Cannot request control with requester None")

    def _control_change(self, *args, value, **kwargs):
        self.controlChange.emit(value)
