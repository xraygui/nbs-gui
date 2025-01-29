from qtpy.QtCore import Signal, QTimer
from ophyd.signal import ReadTimeoutError
from ophyd.utils.errors import DisconnectedError, StatusTimeoutError

from ..views.motor import MotorControl, MotorMonitor
from ..views.motor_tuple import MotorTupleControl, MotorTupleMonitor
from ..views.switchable_motors import (
    SwitchableMotorMonitor,
    SwitchableMotorControl,
)
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

        # Initialize state
        self._setpoint = 0
        self._moving = False

        # Set up timer for checking setpoint
        self.checkValueTimer = QTimer(self)
        self.checkValueTimer.setInterval(500)
        self.checkValueTimer.timeout.connect(self._check_value)
        self.checkValueTimer.start()

        try:
            initial_pos = self.position
            print(f"Got initial position for {name}: {initial_pos}")
            self._setpoint = initial_pos
        except Exception as e:
            print(f"Error getting initial position for {name}: {e}, using 0")

    def _update_moving_status(self, value, **kwargs):
        try:
            self.movingStatusChanged.emit(value)
            self._handle_reconnection()
        except Exception as e:
            self._handle_connection_error(e, "updating moving status")

    def _check_value(self):
        """
        Override base class to handle readback value checking for EPICS motors.
        For EPICS motors, we want to check both position and setpoint.
        """
        try:
            # Get current position
            value = self.position
            self._value_changed(value)

            # Check setpoint
            new_sp = self._obj_setpoint.get(connection_timeout=0.2)
            if new_sp != self._setpoint:
                self._setpoint = new_sp
                self.setpointChanged.emit(self._setpoint)

            self._handle_reconnection()
            self.checkValueTimer.setInterval(500)
        except Exception as e:
            self._handle_connection_error(e, "checking value")
            self.checkValueTimer.setInterval(8000)

    @property
    def setpoint(self):
        return self._setpoint

    @property
    def position(self):
        try:
            pos = self.obj.position
            self._handle_reconnection()
            return pos
        except Exception as e:
            self._handle_connection_error(e, "getting position")
            return 0

    def set(self, value):
        try:
            print(f"[{self.name}] Requesting move to {value}")
            self._obj_setpoint.set(value).wait()
            self._handle_reconnection()
        except Exception as e:
            self._handle_connection_error(e, "setting position")

    def stop(self):
        try:
            self.obj.stop()
            self._handle_reconnection()
        except Exception as e:
            self._handle_connection_error(e, "stopping motor")


class PVPositionerModel(PVModel):
    default_controller = MotorControl
    default_monitor = MotorMonitor
    movingStatusChanged = Signal(bool)
    setpointChanged = Signal(object)

    @property
    def position(self):
        """Get the current position of the motor."""
        try:
            pos = self.obj.position
            self._handle_reconnection()
            return pos
        except Exception as e:
            self._handle_connection_error(e, "getting position")
            return 0

    @property
    def setpoint(self):
        """Get the current setpoint."""
        return self._setpoint

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        print(f"Initializing PVPositionerModel for {name}")
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

        # Initialize state
        self._setpoint = 0
        self._target = 0
        self._moving = False

        # Set up timers
        self.checkSPTimer = QTimer(self)
        self.checkSPTimer.setInterval(1000)
        self.checkSPTimer.timeout.connect(self._check_setpoint)
        self.checkMovingTimer = QTimer(self)
        self.checkMovingTimer.setInterval(500)
        self.checkMovingTimer.timeout.connect(self._check_moving)

        # Start the timers
        self.checkSPTimer.start()
        self.checkMovingTimer.start()

        # Try to get initial position
        try:
            initial_pos = self.position
            print(f"Got initial position for {name}: {initial_pos}")
            self._setpoint = initial_pos
            self._target = initial_pos
        except Exception as e:
            print(f"Error getting initial position for {name}: {e}, using 0")

    def _check_value(self):
        """
        Override base class to handle readback value checking for positioners.
        For positioners, we want the actual position value.
        """
        try:
            # Get the current position directly
            value = self.position
            self._value_changed(value)
            self._handle_reconnection()
            QTimer.singleShot(100000, self._check_value)
        except (ReadTimeoutError, DisconnectedError, StatusTimeoutError) as e:
            self._handle_connection_error(e, "checking value")
            QTimer.singleShot(10000, self._check_value)

    def _check_setpoint(self):
        """
        For pseudo-motors, we track both the target (where we want to go)
        and the setpoint (where we actually end up).
        """
        try:
            if self._moving:
                # During motion, show where we're trying to go
                if self._setpoint != self._target:
                    self._setpoint = self._target
                    self.setpointChanged.emit(self._setpoint)
            else:
                # After motion completes, update to actual position if different
                achieved_pos = float(self.position)
                if abs(achieved_pos - float(self._target)) > abs(
                    float(self._target) * 0.001
                ):
                    print(
                        f"[{self.name}] Move completed: target={self._target}, "
                        f"achieved={achieved_pos}"
                    )
                    self._setpoint = achieved_pos
                    self._target = achieved_pos
                    self.setpointChanged.emit(self._setpoint)

            self._handle_reconnection()
            self.checkSPTimer.setInterval(1000)
        except (ReadTimeoutError, DisconnectedError, StatusTimeoutError) as e:
            self._handle_connection_error(e, "checking setpoint")
            self.checkSPTimer.setInterval(8000)

    def _check_moving(self):
        try:
            moving = self.obj.moving
            self._handle_reconnection()
            self.checkMovingTimer.setInterval(500)
        except (ReadTimeoutError, DisconnectedError, StatusTimeoutError) as e:
            self._handle_connection_error(e, "checking moving status")
            self.checkMovingTimer.setInterval(8000)
            return

        if moving != self._moving:
            self.movingStatusChanged.emit(moving)
            self._moving = moving

    def set(self, value):
        """
        Request a move to a new position.
        Update the target and setpoint immediately to show where we're going.
        """
        try:
            print(f"[{self.name}] Requesting move to {value}")
            self._target = value
            self._setpoint = value
            self.setpointChanged.emit(self._setpoint)
            self.obj.set(value)
            self._handle_reconnection()
        except (ReadTimeoutError, DisconnectedError, StatusTimeoutError) as e:
            self._handle_connection_error(e, "setting position")

    def stop(self):
        try:
            self.obj.stop()
            self._handle_reconnection()
        except (ReadTimeoutError, DisconnectedError, StatusTimeoutError) as e:
            self._handle_connection_error(e, "stopping motor")


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
