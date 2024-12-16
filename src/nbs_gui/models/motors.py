from qtpy.QtCore import Signal, QTimer
from ophyd.signal import ConnectionTimeoutError
from ophyd.utils.errors import DisconnectedError

from ..views.motor import MotorControl, MotorMonitor
from ..views.motor_tuple import MotorTupleControl, MotorTupleMonitor
from ..views.switchable_motors import SwitchableMotorMonitor, SwitchableMotorControl
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
        try:
            new_sp = self._obj_setpoint.get(connection_timeout=0.2)
            self.checkSPTimer.setInterval(1000)
        except (ConnectionTimeoutError, TypeError, DisconnectedError) as e:
            print(f"{e} in {self.label}")
            self.checkSPTimer.setInterval(8000)
            return

        if new_sp != self._setpoint and self._moving:
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
        self.obj.set(value)

    def stop(self):
        self.obj.stop()


class MultiMotorModel(BaseModel):
    """
    Base class for models that contain multiple motors.

    Parameters
    ----------
    name : str
        Name of the model
    obj : object
        The device object containing motors
    group : str
        Group this model belongs to
    long_name : str
        Human readable name
    show_real_motors_by_default : bool, optional
        Whether to show real motors by default instead of pseudo motors
    """

    default_controller = SwitchableMotorControl
    default_monitor = SwitchableMotorMonitor

    def __init__(
        self, name, obj, group, long_name, show_real_motors_by_default=False, **kwargs
    ):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.real_motors = []
        self.pseudo_motors = []
        self.show_real_motors_by_default = show_real_motors_by_default


class MotorTupleModel(MultiMotorModel):
    """
    Model for a tuple of real motors.

    Parameters
    ----------
    name : str
        Name of the model
    obj : object
        The device object containing motors
    group : str
        Group this model belongs to
    long_name : str
        Human readable name
    show_real_motors_by_default : bool, optional
        Whether to show real motors by default instead of pseudo motors
    """

    default_controller = MotorTupleControl
    default_monitor = MotorTupleMonitor

    def __init__(
        self, name, obj, group, long_name, show_real_motors_by_default=True, **kwargs
    ):
        super().__init__(
            name,
            obj,
            group,
            long_name,
            show_real_motors_by_default=show_real_motors_by_default,
            **kwargs,
        )

        # Create models for real motors
        self.real_motors = [
            MotorModel(
                name=getattr(obj, attrName).name,
                obj=getattr(obj, attrName),
                group=group,
                long_name=getattr(obj, attrName).name,
            )
            for attrName in obj.component_names
        ]

        # For compatibility with switchable views, we use real_motors as pseudo_motors
        # since they are what we want to show by default
        self.pseudo_motors = self.real_motors


class PseudoPositionerModel(MultiMotorModel):
    """
    Model for pseudo positioners with both real and pseudo motors.

    Parameters
    ----------
    name : str
        Name of the model
    obj : object
        The pseudo positioner object
    group : str
        Group this model belongs to
    long_name : str
        Human readable name
    show_real_motors_by_default : bool, optional
        Whether to show real motors by default instead of pseudo motors
    """

    def __init__(
        self, name, obj, group, long_name, show_real_motors_by_default=False, **kwargs
    ):
        super().__init__(
            name,
            obj,
            group,
            long_name,
            show_real_motors_by_default=show_real_motors_by_default,
            **kwargs,
        )

        # Create models for real motors
        self.real_motors = [
            MotorModel(
                name=real_axis.name,
                obj=real_axis,
                group=group,
                long_name=real_axis.name,
            )
            for real_axis in obj.real_positioners
        ]

        # Create models for pseudo motors
        self.pseudo_motors = [
            PVPositionerModel(
                name=ps_axis.name,
                obj=ps_axis,
                group=group,
                long_name=ps_axis.name,
            )
            for ps_axis in obj.pseudo_positioners
        ]
