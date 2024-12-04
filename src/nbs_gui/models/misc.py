from qtpy.QtCore import Signal, QTimer

from ..widgets.gatevalve import GVControl, GVMonitor
from ..widgets.energy import EnergyControl, EnergyMonitor
from ..widgets.manipulator_monitor import RealManipulatorControl, RealManipulatorMonitor

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
        self.sub_key = self.obj.target.subscribe(self._value_changed, run=True)
        timer = QTimer.singleShot(5000, self._check_value)

    def _cleanup(self):
        print(f"Cleaning up {self.name}")
        self.obj.target.unsubscribe(self.sub_key)

    def _check_value(self):
        try:
            value = self.obj.get(connection_timeout=0.2, timeout=0.2)
            self._value_changed(value)
            QTimer.singleShot(100000, self._check_value)
        except:
            QTimer.singleShot(10000, self._check_value)

    def _value_changed(self, value, **kwargs):
        if self.value_type is None:
            if isinstance(value, float):
                self.value_type = float
            elif isinstance(value, int):
                self.value_type = int
            elif isinstance(value, str):
                self.value_type = str
            else:
                self.value_type = type(value)
        try:
            if self.value_type is float:
                value = formatFloat(value)
            elif self.value_type is int:
                value = formatInt(value)
            else:
                value = str(value)
        except ValueError:
            self.value_type = None
            return
        self.valueChanged.emit(value)


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


class EnergyAxesModel(BaseModel):
    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.real_axes_models = [
            PVPositionerModel(
                name=real_axis.name,
                obj=real_axis,
                group=group,
                long_name=real_axis.name,
            )
            for real_axis in obj.real_positioners
        ]
        self.pseudo_axes_models = [
            PVPositionerModel(
                name=ps_axis.name, obj=ps_axis, group=group, long_name=ps_axis.name
            )
            for ps_axis in obj.pseudo_positioners
        ]


class ManipulatorModel(BaseModel):
    default_controller = RealManipulatorControl
    default_monitor = RealManipulatorMonitor

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.real_axes_models = [
            MotorModel(
                name=real_axis.name,
                obj=real_axis,
                group=group,
                long_name=real_axis.name,
            )
            for real_axis in obj.real_positioners
        ]
        self.pseudo_axes_models = [
            PVPositionerModel(
                name=ps_axis.name, obj=ps_axis, group=group, long_name=ps_axis.name
            )
            for ps_axis in obj.pseudo_positioners
        ]
