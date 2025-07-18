from qtpy.QtCore import Signal, QTimer
from ophyd.signal import ReadTimeoutError, ConnectionTimeoutError
from ophyd.utils.errors import DisconnectedError, StatusTimeoutError
from epics.ca import ChannelAccessGetFailure

from ..views.motor import MotorControl, MotorMonitor
from ..views.motor_tuple import MotorTupleControl, MotorTupleMonitor
from ..views.switchable_motors import (
    SwitchableMotorMonitor,
    SwitchableMotorControl,
)
from .base import PVModel, BaseModel, requires_connection, initialize_with_retry

CONNECTION_ERRORS = (
    ReadTimeoutError,
    DisconnectedError,
    ConnectionTimeoutError,
    StatusTimeoutError,
    ChannelAccessGetFailure,
)


def MotorModel(name, obj, group, long_name, **kwargs):
    # print(f"Checking which MotorModel to create for {name}")
    # Disconnected motors will sometimes throw errors when checking for attributes...
    if "motor_is_moving" in obj.__dir__():
        # print(f"Creating EPICSMotorModel for {name}")
        return EPICSMotorModel(name, obj, group, long_name, **kwargs)
    elif "moving" in obj.__dir__():
        # print(f"Creating PVPositionerModel for {name}")
        return PVPositionerModel(name, obj, group, long_name, **kwargs)
    else:
        raise AttributeError(
            f"{name} has neither moving nor motor_is_moving attributes"
        )


class BaseMotorModel(PVModel):
    default_controller = MotorControl
    default_monitor = MotorMonitor
    movingStatusChanged = Signal(bool)
    setpointChanged = Signal(object)

    def _stop_timers(self):
        """Stop all timers when device becomes disconnected."""
        # Override in subclasses to stop specific timers
        pass

    def _start_timers(self):
        """Start all timers when device becomes reconnected."""
        # Override in subclasses to start specific timers
        pass

    def _handle_connection_change(self, connected):
        """
        Handle connection status changes by stopping/starting timers.

        Parameters
        ----------
        connected : bool
            Whether the device is now connected
        """
        if connected:
            print(f"[{self.name}] Device connected, starting timers")
            self._start_timers()
        else:
            print(f"[{self.name}] Device disconnected, stopping timers")
            self._stop_timers()

    @property
    def moving(self):
        return self._moving

    @property
    def position(self):
        # print(f"[{self.name}.position] Getting position")
        pos = self._get_position()
        # print(f"[{self.name}.position] Got position: {pos}")
        return pos

    @property
    def limits(self):
        return self._get_limits()

    @requires_connection
    def stop(self):
        self.obj.stop()

    @requires_connection
    def _get_limits(self):
        if hasattr(self.obj, "limits"):
            return self.obj.limits
        else:
            return (None, None)


class EPICSMotorModel(BaseMotorModel):

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.units = None
        self._obj_setpoint = None
        self._obj_readback = None
        self._setpoint = None
        self._position = None
        self._moving = False
        self.checkValueTimer = QTimer(self)
        EPICSMotorModel._initialize(self)

    def _stop_timers(self):
        """Stop all timers when device becomes disconnected."""
        if self.checkValueTimer.isActive():
            self.checkValueTimer.stop()
            print(f"[{self.name}] Stopped checkValueTimer")

    def _start_timers(self):
        """Start all timers when device becomes reconnected."""
        if not self.checkValueTimer.isActive():
            self.checkValueTimer.start()
            print(f"[{self.name}] Started checkValueTimer")

    @initialize_with_retry
    def _initialize(self):
        if not super()._initialize():
            return False

        print(f"Initializing EPICSMotorModel for {self.name}")
        self.obj.motor_is_moving.subscribe(self._update_moving_status)

        # print(f"Setting up setpoint for {self.name}")
        if "user_setpoint" in self.obj.__dir__():
            # print(f"Using user_setpoint for {self.name}._obj_setpoint")
            self._obj_setpoint = self.obj.user_setpoint
        elif "setpoint" in self.obj.__dir__():
            # print(f"Using setpoint for {self.name}._obj_setpoint")
            self._obj_setpoint = self.obj.setpoint
        else:
            # print(f"Using obj for {self.name}._obj_setpoint")
            self._obj_setpoint = self.obj

        if hasattr(self.obj, "user_readback"):
            self._obj_readback = self.obj.user_readback
        elif hasattr(self.obj, "readback"):
            self._obj_readback = self.obj.readback
        else:
            self._obj_readback = self.obj

        if hasattr(self._obj_setpoint, "metadata"):
            self.units = self._obj_setpoint.metadata.get("units", None)
        else:
            self.units = None
        print(f"{self.name} has units {self.units}")

        # Initialize state

        # Set up timer for checking setpoint

        # Get initial position -- not initialized yet, so don't check connection!
        self._position = self._get_position(check_connection=False)
        print(f"Got initial position for {self.name}: {self._position}")
        self._setpoint = self._position
        self.setpointChanged.emit(self._setpoint)

        self.checkValueTimer.setInterval(1000)
        self.checkValueTimer.timeout.connect(self._check_value)
        self.checkValueTimer.start()

        return True

    def _update_moving_status(self, value, **kwargs):
        self._moving = value
        self.movingStatusChanged.emit(value)

    @requires_connection
    def _check_value(self):
        """
        Override base class to handle readback value checking for EPICS motors.
        For EPICS motors, we want to check both position and setpoint.
        """
        try:
            # Get current position
            value = self.position
            self._value_changed(value)
            # print(f"[{self.name}] check_value: {value}")
            # Check setpoint
            new_sp = self._get_setpoint()
            if new_sp is None:
                self._setpoint = None
                self.setpointChanged.emit(self._setpoint)
            elif new_sp != self._setpoint:
                self._setpoint = new_sp
                self.setpointChanged.emit(self._setpoint)
            # Timer interval is managed by connection status now
        except (TypeError, ValueError) as e:
            self._handle_connection_error(e, "checking value")

    @property
    def setpoint(self):
        return self._setpoint

    @requires_connection
    def _get_position(self):
        try:
            return self._obj_readback.get(connection_timeout=0.2)
        except Exception as e:
            print(
                f"[EPICSMotorModel._get_position] Error getting position for {self.name}: {e}, using None"
            )
            raise e

    @requires_connection
    def _get_setpoint(self):
        return self._obj_setpoint.get(connection_timeout=0.2)

    @requires_connection
    def set(self, value):
        print(f"[{self.name}] Requesting move to {value}")
        try:
            self._obj_setpoint.set(value).wait()
        except (ValueError, TypeError) as e:
            msg = f"Value {value} cannot be set: {e}"
            raise ValueError(msg) from e
        return value


class PVPositionerModel(BaseMotorModel):

    def __init__(self, name, obj, group, long_name, **kwargs):
        print(f"[{name}.__init__] Initializing PVPositionerModel")
        super().__init__(name, obj, group, long_name, **kwargs)
        self._setpoint = None
        self._target = None
        self._moving = False
        self._obj_setpoint = None
        self._obj_readback = None
        self.units = None
        self.checkSPTimer = QTimer(self)
        self.checkMovingTimer = QTimer(self)
        self.checkValueTimer = QTimer(self)
        print(f"[{name}.__init__] about to call _initialize")
        PVPositionerModel._initialize(self)

    def _stop_timers(self):
        """Stop all timers when device becomes disconnected."""
        if self.checkSPTimer.isActive():
            self.checkSPTimer.stop()
            print(f"[{self.name}] Stopped checkSPTimer")
        if self.checkMovingTimer.isActive():
            self.checkMovingTimer.stop()
            print(f"[{self.name}] Stopped checkMovingTimer")
        if self.checkValueTimer.isActive():
            self.checkValueTimer.stop()
            print(f"[{self.name}] Stopped checkValueTimer")

    def _start_timers(self):
        """Start all timers when device becomes reconnected."""
        if not self.checkSPTimer.isActive():
            self.checkSPTimer.start()
            print(f"[{self.name}] Started checkSPTimer")
        if not self.checkMovingTimer.isActive():
            self.checkMovingTimer.start()
            print(f"[{self.name}] Started checkMovingTimer")
        if not self.checkValueTimer.isActive():
            self.checkValueTimer.start()
            print(f"[{self.name}] Started checkValueTimer")

    @initialize_with_retry
    def _initialize(self):
        print(f"[{self.name}._initialize] Initializing PVPositionerModel")
        if not super()._initialize():
            return False

        if hasattr(self.obj, "user_setpoint"):
            self._obj_setpoint = self.obj.user_setpoint
        elif hasattr(self.obj, "setpoint"):
            self._obj_setpoint = self.obj.setpoint
        else:
            self._obj_setpoint = self.obj

        if hasattr(self.obj, "user_readback"):
            self._obj_readback = self.obj.user_readback
        elif hasattr(self.obj, "readback"):
            self._obj_readback = self.obj.readback
        else:
            self._obj_readback = self.obj

        if hasattr(self._obj_setpoint, "metadata"):
            self.units = self._obj_setpoint.metadata.get("units", None)
        else:
            self.units = None
        print(f"{self.name} has units {self.units}")

        # Initialize state

        # Set up timers
        self.checkSPTimer.setInterval(1000)
        self.checkSPTimer.timeout.connect(self._check_setpoint)

        self.checkMovingTimer.setInterval(500)
        self.checkMovingTimer.timeout.connect(self.check_moving)

        # Start the timers

        self.checkValueTimer.setInterval(500)
        self.checkValueTimer.timeout.connect(self._check_value)

        self.checkSPTimer.start()
        self.checkMovingTimer.start()
        self.checkValueTimer.start()
        # Try to get initial position
        try:
            initial_pos = self._get_position(check_connection=False)
            print(f"Got initial position for {self.name}: {initial_pos}")

            self._setpoint = initial_pos
            self._target = initial_pos
            self.setpointChanged.emit(self._setpoint)

        except Exception as e:
            print(f"Error getting initial position for {self.name}: {e}, using 0")
        print(f"Initialized PVPositionerModel for {self.name}")
        return True

    @requires_connection
    def _get_position(self):
        try:
            return self._obj_readback.get(timeout=0.2, connection_timeout=0.2)
        except Exception as e:
            print(
                f"[PVPositionerModel._get_position] Error getting position for {self.name}: {e}, using None"
            )
            raise e

    @property
    def setpoint(self):
        """Get the current setpoint."""
        return self._setpoint

    @requires_connection
    def _check_value(self):
        """
        Override base class to handle readback value checking for positioners.
        For positioners, we want the actual position value.
        """
        value = self.position
        self._value_changed(value)
        # print(f"[{self.name}] check_value: {value}")
        # Timer interval is managed by connection status now

    @requires_connection
    def _check_setpoint(self):
        """
        For pseudo-motors, we track both the target (where we want to go)
        and the setpoint (where we actually end up).
        """
        # print(f"[{self.name}._check_setpoint] Checking setpoint")
        try:
            if not all(
                isinstance(x, (int, float))
                for x in [self.setpoint, self._target, self.position]
            ):
                return
        except (TypeError, ValueError):
            return
        # print(f"[{self.name}] getting sp")
        try:
            if self._moving:
                # During motion, show where we're trying to go
                if self._setpoint != self._target:
                    # print(
                    #     f"[{self.name}._check_setpoint] Updating setpoint to {self._target}"
                    # )

                    self._setpoint = self._target
                    self.setpointChanged.emit(self.setpoint)
            else:
                # After motion completes, update to actual position if different
                achieved_pos = float(self.position)
                target = float(self._target)
                if abs(achieved_pos - target) > abs(float(target) * 0.01):
                    # print(
                    #     f"[{self.name}] Move completed: target={self._target}, "
                    #     f"achieved={achieved_pos}"
                    # )
                    self._setpoint = achieved_pos
                    self._target = achieved_pos

                    self.setpointChanged.emit(self.setpoint)

            # Timer interval is managed by connection status now
        except (TypeError, ValueError, AttributeError) as e:
            self._handle_connection_error(e, "checking setpoint")
        # print(f"[{self.name}] done getting sp")

    @requires_connection
    def _check_moving(self):
        moving = self.obj.moving
        return moving

    def check_moving(self):
        # print(f"[{self.name}] getting move status")
        moving = self._check_moving()
        if moving is not None:
            # Timer interval is managed by connection status now
            pass
        else:
            # Timer interval is managed by connection status now
            return

        if moving != self._moving and isinstance(moving, bool):
            self.movingStatusChanged.emit(moving)
            self._moving = moving
        # print(f"[{self.name}] Done getting move status, {moving}")

    @requires_connection
    def set(self, value):
        """
        Request a move to a new position.
        Update the target and setpoint immediately to show where we're going.
        """

        print(f"[{self.name}] Requesting move to {value}")
        self._target = value
        self._setpoint = value
        self.setpointChanged.emit(self._setpoint)
        self.obj.set(value)
        print(f"[{self.name}] Done requesting move")


class PseudoSingleModel(PVPositionerModel):

    def _check_connection(self, retry_on_failure=True):
        """
        Check connection and handle reconnection attempts.
        All connection checking and reconnection logic lives here.

        For pseudoaxes we need to check the connection of the parent object
        """
        # Clear the scheduled flag since we're now doing the check
        self._reconnection_scheduled = False

        try:
            if "wait_for_connection" in dir(self.obj.parent):
                print(f"[{self.name}._check_connection] Waiting for connection")
                self.obj.parent.wait_for_connection(timeout=0.2)
                connected = True
            else:
                print(f"[{self.name}._check_connection] Getting value")
                self.obj.get(timeout=0.2, connection_timeout=0.2)
                connected = True
        except Exception as e:
            print(f"[{self.name}._check_connection] Error: {e}")
            connected = False
        print(f"[{self.name}._check_connection] Connected: {connected}")

        # Update connection state if changed
        if connected != self._connected:
            # If we aren't initialized, we can't be considered fully connected
            # so we only emit the signal if we are both connected and initialized
            # we still need to return the connected status so that initialization
            # can happen
            connected_and_initialized = connected and self.initialized
            if self._connected != connected_and_initialized:
                self._connected = connected_and_initialized
                self.connectionStatusChanged.emit(self._connected)

            # Reset reconnection attempts on successful connection
            if connected:
                self._reconnection_attempts = 0
                print(
                    f"[{self.name}] Connection restored, resetting reconnection attempts"
                )

            # If we're now connected, try initialization
            if not connected and retry_on_failure:
                self._reconnection_attempts += 1
                self._schedule_reconnection()

        return connected


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
        print(f"Loading MotorTupleModel for {self.label}")
        # Create models for real motors
        self.real_motors = []
        for attrName in obj.component_names:

            motor = MotorModel(
                name=getattr(obj, attrName).name,
                obj=getattr(obj, attrName),
                group=group,
                long_name=getattr(obj, attrName).name,
            )
            # print(f"Created motor model: {motor.label}")
            self.real_motors.append(motor)

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
        print(f"[{self.name}] Intializing PseudoPositionerModel")
        print(f"[{self.name}] Creating real motors")
        self.real_motors = [
            MotorModel(
                name=real_axis.name,
                obj=real_axis,
                group=group,
                long_name=real_axis.name,
            )
            for real_axis in obj.real_positioners
        ]
        print(f"[{self.name}] Created {len(self.real_motors)} real motors")
        # Create models for pseudo motors
        print(f"[{self.name}] Creating pseudo motors")
        self.pseudo_motors = [
            PseudoSingleModel(
                name=ps_axis.name,
                obj=ps_axis,
                group=group,
                long_name=ps_axis.name,
            )
            for ps_axis in obj.pseudo_positioners
        ]
        print(f"[{self.name}] Created {len(self.pseudo_motors)} pseudo motors")
