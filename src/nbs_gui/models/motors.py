from qtpy.QtCore import Signal, QTimer
from ophyd.signal import ConnectionTimeoutError
from ophyd.utils.errors import DisconnectedError

from ..widgets.motor import MotorControl, MotorMonitor
from ..widgets.manipulator_monitor import RealManipulatorControl, RealManipulatorMonitor
from .base import PVModel, BaseModel


def MotorModel(name, obj, group, long_name, **kwargs):
    if hasattr(obj, "motor_is_moving"):
        return EPICSMotorModel(name, obj, group, long_name, **kwargs)
    elif hasattr(obj, "moving"):
        return PVPositionerModel(name, obj, group, long_name, **kwargs)
    else:
        raise AttributeError(
            f"{name} has neither moving nor motor_is_moving attributes"
        )


class EPICSMotorModel(PVModel):
    default_controller = MotorControl
    default_monitor = MotorMonitor
    movingStatusChanged = Signal(bool)
    setpointChanged = Signal(object)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.obj.motor_is_moving.subscribe(self._update_moving_status)
        if hasattr(self.obj, "user_setpoint"):
            self._obj_setpoint = self.obj.user_setpoint
        elif hasattr(self.obj, "setpoint"):
            self._obj_setpoint = self.obj.setpoint
        else:
            self._obj_setpoint = self.obj

        if hasattr(self._obj_setpoint, "metadata"):
            self.units = self._obj_setpoint.metadata.get("units", None)
        else:
            self.units = None
        print(f"{name} has units {self.units}")
        self._setpoint = 0
        self.checkSelfTimer = QTimer(self)
        self.checkSelfTimer.setInterval(500)
        self.checkSelfTimer.timeout.connect(self._check_self)
        self.checkSelfTimer.start()

    def _update_moving_status(self, value, **kwargs):
        self.movingStatusChanged.emit(value)

    def _check_self(self):
        try:
            new_sp = self._obj_setpoint.get(connection_timeout=0.2)
            self.checkSelfTimer.setInterval(500)
        except (ConnectionTimeoutError, DisconnectedError) as e:
            print(f"{e} in {self.label}")
            self.checkSelfTimer.setInterval(8000)
            return
        if new_sp != self._setpoint:
            self._setpoint = new_sp
            self.setpointChanged.emit(self._setpoint)

    @property
    def setpoint(self):
        return self._setpoint

    @property
    def position(self):
        try:
            return self.obj.position
        except:
            return 0

    def set(self, value):
        self._obj_setpoint.set(value).wait()

    def stop(self):
        self.obj.stop()


class PVPositionerModel(PVModel):
    default_controller = MotorControl
    default_monitor = MotorMonitor
    movingStatusChanged = Signal(bool)
    setpointChanged = Signal(object)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        print("Initializing PVPositionerModel")
        if hasattr(self.obj, "user_setpoint"):
            self._obj_setpoint = self.obj.user_setpoint
        elif hasattr(self.obj, "setpoint"):
            self._obj_setpoint = self.obj.setpoint
        else:
            self._obj_setpoint = self.obj

        if hasattr(self._obj_setpoint, "metadata"):
            self.units = self._obj_setpoint.metadata.get("units", None)
        else:
            self.units = None
        print(f"{name} has units {self.units}")
        self._setpoint = 0
        self._moving = False
        self.checkSPTimer = QTimer(self)
        self.checkSPTimer.setInterval(1000)
        self.checkSPTimer.timeout.connect(self._check_setpoint)
        self.checkMovingTimer = QTimer(self)
        self.checkMovingTimer.setInterval(500)
        self.checkMovingTimer.timeout.connect(self._check_moving)
        # Start the timer
        self.checkSPTimer.start()
        self.checkMovingTimer.start()
        print("Done Initializing")

    def _check_value(self):
        try:
            value = self.obj.readback.get(connection_timeout=0.2, timeout=0.2)
            new_sp = self._obj_setpoint.get(connection_timeout=0.2)
            self._value_changed(value)
            self.setpointChanged.emit(new_sp)
            QTimer.singleShot(100000, self._check_value)
        except:
            QTimer.singleShot(10000, self._check_value)

    def _check_setpoint(self):
        # Timeout errors self-explanatory. TypeErrors occur when a pseudopositioner times out and
        # tries to do an inverse calculation anyway
        try:
            new_sp = self._obj_setpoint.get(connection_timeout=0.2)
            self.checkSPTimer.setInterval(1000)
        except (ConnectionTimeoutError, TypeError, DisconnectedError) as e:
            print(f"{e} in {self.label}")
            self.checkSPTimer.setInterval(8000)
            return

        if new_sp != self._setpoint and self._moving:
            # print(self.label, new_sp, self._setpoint, type(new_sp))
            self._setpoint = new_sp
            self.setpointChanged.emit(self._setpoint)

    def _check_moving(self):
        try:
            moving = self.obj.moving
            self.checkMovingTimer.setInterval(500)
        except (ConnectionTimeoutError, DisconnectedError) as e:
            print(f"{e} in {self.label} moving")
            self.checkMovingTimer.setInterval(8000)
            return

        if moving != self._moving:
            self.movingStatusChanged.emit(moving)
            self._moving = moving

    @property
    def setpoint(self):
        return self._setpoint

    def set(self, value):
        # print("Setting {self.name} to {value}")
        self.obj.set(value)

    def stop(self):
        self.obj.stop()


class MotorTupleModel(BaseModel):
    default_controller = RealManipulatorControl
    default_monitor = RealManipulatorMonitor

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.real_axes_models = []
        for attrName in obj.component_names:
            axis = getattr(obj, attrName)
            self.real_axes_models.append(
                MotorModel(name=axis.name, obj=axis, group=group, long_name=axis.name)
            )


class PseudoPositionerModel(BaseModel):
    # Needs to check real_axis for PVPositioner or Motor
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
