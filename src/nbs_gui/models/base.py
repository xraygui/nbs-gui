from qtpy.QtCore import Signal, QTimer
from qtpy.QtWidgets import QWidget
import numpy as np
from ophyd.signal import ReadTimeoutError, ConnectionTimeoutError
from ophyd.utils.errors import DisconnectedError, StatusTimeoutError
from epics.ca import ChannelAccessGetFailure
from ..views.monitors import PVMonitor, PVControl
from ..views.enums import EnumControl, EnumMonitor
from .mixins import ModeManagedModel
from functools import wraps
from random import uniform

CONNECTION_ERRORS = (
    ReadTimeoutError,
    DisconnectedError,
    ConnectionTimeoutError,
    StatusTimeoutError,
    ChannelAccessGetFailure,
)


def initialize_with_retry(func, retry_intervals=None, jitter_factor=0.2):
    """
    Decorator for initialization methods with exponential backoff and jitter.

    Parameters
    ----------
    func : callable
        The function to decorate
    retry_intervals : list of int, optional
        Base intervals in ms. Defaults to [1000, 30000, 60000, 120000]
    jitter_factor : float, optional
        Random jitter factor (0-1). Actual delay will be interval ± factor*interval
    """
    BASE_INTERVALS = retry_intervals or [1000, 30000, 60000, 120000]

    def get_jittered_interval(base_interval):
        """Add random jitter to interval."""
        jitter = uniform(-jitter_factor, jitter_factor) * base_interval
        return int(base_interval + jitter)

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "_initialized_methods"):
            self._initialized_methods = set()
        if not hasattr(self, "_uninitialized_methods"):
            self._uninitialized_methods = set()
        if not hasattr(self, "_init_retry_counts"):
            self._init_retry_counts = {}
        if not hasattr(self, "_init_retry_timers"):
            self._init_retry_timers = {}

        qual_name = func.__qualname__

        # If already initialized successfully, return True
        if qual_name in self._initialized_methods:
            return True
        elif qual_name not in self._uninitialized_methods:
            self._uninitialized_methods.add(qual_name)

        # If a retry timer is already running, just return False
        if qual_name in self._init_retry_timers:
            timer = self._init_retry_timers[qual_name]
            if timer.isActive():
                # print(f"Retry already scheduled for {qual_name}, " "waiting for timer")
                return False

        try:
            # Run the initialization method
            result = func(self, *args, **kwargs)

            # If successful, mark as initialized and clean up
            if result:
                self._initialized_methods.add(qual_name)
                if qual_name in self._init_retry_counts:
                    del self._init_retry_counts[qual_name]
                if qual_name in self._init_retry_timers:
                    timer = self._init_retry_timers[qual_name]
                    if timer.isActive():
                        timer.stop()
                    del self._init_retry_timers[qual_name]
                self._uninitialized_methods.remove(qual_name)
                if len(self._uninitialized_methods) == 0:
                    # If we've just initialized all methods, check connection
                    self._check_connection(retry_on_failure=False)
                return True
            else:
                # Get/increment retry count
                retry_count = self._init_retry_counts.get(qual_name, 0)
                self._init_retry_counts[qual_name] = retry_count + 1

                # Get base interval and add jitter
                base_interval = BASE_INTERVALS[
                    min(retry_count, len(BASE_INTERVALS) - 1)
                ]
                interval = get_jittered_interval(base_interval)

                # Create and store new timer
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: wrapper(self, *args, **kwargs))
                self._init_retry_timers[qual_name] = timer

                print(
                    f"[{self.name}.{qual_name}] Initialization failed with result {result}, "
                    f"attempt {retry_count + 1}, retrying in {interval/1000:.1f}s"
                )
                timer.start(interval)
                return False

        except Exception as e:
            # Handle exceptions same as failed initialization
            print(
                f"[{self.name}.{qual_name}] Initialization failed with exception: {e}"
            )

            retry_count = self._init_retry_counts.get(qual_name, 0)
            self._init_retry_counts[qual_name] = retry_count + 1

            base_interval = BASE_INTERVALS[min(retry_count, len(BASE_INTERVALS) - 1)]
            interval = get_jittered_interval(base_interval)

            # Create and store new timer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: wrapper(self, *args, **kwargs))
            self._init_retry_timers[qual_name] = timer

            print(
                f"Retrying {qual_name} after error, "
                f"attempt {retry_count + 1}, in {interval/1000:.1f}s"
            )
            timer.start(interval)
            return False

    return wrapper


def formatFloat(value, precision=2, width=None):
    """Format a float value with appropriate precision and width.

    Parameters
    ----------
    value : any
        Value to format, will attempt to convert to float
    precision : int, optional
        Number of decimal places to show
    width : int, optional
        Total width of the formatted string. If None, width is calculated
        to accommodate sign, precision, and scientific notation

    Returns
    -------
    str
        Formatted string representation of the value
    """
    try:
        float_val = float(value)

        if abs(float_val) >= 10 ** (1 - precision):
            fmtstr = f"{{:.{precision}f}}"
            min_width = precision + 3  # +3 for sign, units digit, decimal
        elif float_val == 0:
            fmtstr = f"{{:.{precision}f}}"
            min_width = precision + 3  # +3 for sign, units digit, decimal
        else:
            fmtstr = f"{{:.{precision}e}}"
            min_width = precision + 7  # +7 for sign, decimal, e+xx

        result = fmtstr.format(float_val)
        final_width = width if width is not None else min_width
        return f"{result:>{final_width}}"
    except (ValueError, TypeError) as e:
        print(f"Could not convert value {value} to float: {e}")
        return str(value)  # Return as string if conversion fails


def formatInt(value):
    """Format an integer value."""
    try:
        return "{:d}".format(int(value))
    except (ValueError, TypeError) as e:
        print(f"Could not convert value {value} to int: {e}")
        return str(value)  # Return as string if conversion fails


def requires_connection(func, default_value=None):
    """
    Decorator to ensure a method only runs when device is connected.
    If not connected, triggers a connection check which will handle
    reconnection attempts.

    Parameters
    ----------
    func : callable
        The method to wrap

    Returns
    -------
    callable
        The wrapped method that checks connection status
    """

    @wraps(func)
    def wrapper(self, *args, check_connection=True, **kwargs):
        if hasattr(self, "initialized") and not self.initialized and check_connection:
            print(f"Device {self.name} not initialized for {func.__name__}")
            return default_value
        elif not hasattr(self, "initialized"):
            print(f"[{self.name}.{func.__name__}] Device has no initialized attribute")

        if not self.connected and check_connection:
            print(
                f"[{self.name}.{func.__name__}] Device {self.name} not connected for {func.__name__}"
            )
            # Schedule reconnection instead of immediate check to prevent blocking
            self._schedule_reconnection()
            print(
                f"[{self.name}.{func.__name__}] returning default value {default_value}"
            )
            return default_value

        try:
            return func(self, *args, **kwargs)
        except CONNECTION_ERRORS as e:
            print(
                f"[{self.name}.{func.__name__}] Connection status was {self.connected}, Connection error: {e}"
            )
            # Schedule reconnection instead of immediate check to prevent blocking
            self._schedule_reconnection()
            return default_value

    return wrapper


class BaseModel(QWidget, ModeManagedModel):
    default_controller = None
    default_monitor = PVMonitor
    connectionStatusChanged = Signal(bool)

    def __init__(self, name, obj, group, long_name, **kwargs):
        print(f"[{name}.__init__] Initializing BaseModel")
        super().__init__()
        self.name = name
        self.obj = obj
        self.group = group
        self.label = long_name
        self.enabled = True
        self._connected = False  # Start as disconnected
        self._value = None
        self._latest_value = None
        self._has_update = False
        # Create reconnection timer
        self._reconnection_timer = QTimer()
        self._reconnection_timer.timeout.connect(self._check_connection)
        self._reconnection_timer.setSingleShot(True)
        self._reconnection_scheduled = False  # Track if reconnection is scheduled
        self._reconnection_attempts = 0  # Count attempts since last connection
        self._uninitialized_methods = set()
        # Set common attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Try initial connection - call BaseModel._initialize explicitly
        # to avoid calling derived class _initialize methods before they're ready
        BaseModel._initialize(self)

        # Connect connection status changes to timer management
        self.connectionStatusChanged.connect(self._handle_connection_change)

        self.destroyed.connect(lambda: self._cleanup)
        self.units = None

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
    def initialized(self):
        return len(self._uninitialized_methods) == 0

    @initialize_with_retry
    def _initialize(self):
        """Base initialization"""
        print(f"[{self.name}._initialize] Initializing BaseModel")
        result = self._check_connection(retry_on_failure=False)
        if result:
            print(f"[{self.name}._initialize] Initialized BaseModel")
        return result

    def _cleanup(self):
        pass

    def _handle_connection_error(self, error, context=""):
        """
        Common handler for connection errors.

        Parameters
        ----------
        error : Exception
            The error that occurred
        context : str, optional
            Additional context about where the error occurred
        """
        if self._connected:
            self._connected = False
            self.connectionStatusChanged.emit(False)
            print(f"Connection error for {self.name} {context}: {error}")

    def _schedule_reconnection(self):
        """
        Schedule a reconnection attempt if not already scheduled.
        This prevents multiple simultaneous reconnection requests.
        Uses exponential backoff: 10s * attempts, capped at 60s.
        """
        if not self._reconnection_scheduled and not self._reconnection_timer.isActive():
            # Calculate backoff delay: 10s * attempts, capped at 60s
            delay = min(10000 * (self._reconnection_attempts + 1), 60000)
            print(
                f"Starting reconnection timer for {self.name} (attempt {self._reconnection_attempts + 1}, delay: {delay/1000:.1f}s)"
            )
            self._reconnection_scheduled = True
            self._reconnection_timer.start(delay)

    def _check_connection(self, retry_on_failure=True):
        """
        Check connection and handle reconnection attempts.
        All connection checking and reconnection logic lives here.
        """
        # Clear the scheduled flag since we're now doing the check
        self._reconnection_scheduled = False

        try:
            if "wait_for_connection" in dir(self.obj):
                # print(f"[{self.name}._check_connection] Waiting for connection")
                self.obj.wait_for_connection(timeout=0.2)
                connected = True
            else:
                # print(f"[{self.name}._check_connection] Getting value")
                self.obj.get(timeout=0.2, connection_timeout=0.2)
                connected = True
        except Exception as e:
            print(f"[{self.name}._check_connection] Error: {e}")
            connected = False
        # print(f"[{self.name}._check_connection] Connected: {connected}")

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

    @property
    def connected(self):
        """Whether the device is currently connected."""
        return self._connected

    def _value_changed(self, value, **kwargs):
        raise NotImplementedError("Subclasses must implement _value_changed")

    def _stash_value(self, value, **kwargs):
        """
        Store the latest value from a subscription callback.

        Parameters
        ----------
        value : any
            Latest value from the device.
        """
        self._latest_value = value
        self._has_update = True

    def drain_pending(self):
        """
        Emit a pending update if one exists.

        Returns
        -------
        bool
            True if an update was emitted, otherwise False.
        """
        if not self._has_update:
            return False
        value = self._latest_value
        self._latest_value = None
        self._has_update = False
        self._value_changed(value)
        return True

    def iter_models(self):
        """
        Yield contained models for traversal.

        Yields
        ------
        BaseModel
            Contained models.
        """
        return ()


class PVModelRO(BaseModel):
    valueChanged = Signal(str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        # print(f"[{name}.__init__] Initializing PVModelRO")
        super().__init__(name, obj, group, long_name, **kwargs)
        # print(f"[{name}.__init__] about to call _initialize")
        PVModelRO._initialize(self)

    @initialize_with_retry
    def _initialize(self):
        # print(f"[{self.name}._initialize] Initializing PVModelRO")
        if not super()._initialize():
            self.value_type = None
            self.units = None
            return False

        if hasattr(self.obj, "metadata"):
            self.units = self.obj.metadata.get("units", None)
            # print(f"{self.name} has units {self.units}")
        else:
            self.units = None
            # print(f"{self.name} has no metadata")

        try:
            _value_type = self.obj.describe().get("dtype", None)
            if _value_type == "integer":
                self.value_type = int
            elif _value_type == "number":
                self.value_type = float
            elif _value_type == "string":
                self.value_type = str
            else:
                self.value_type = None
        except Exception as e:
            print(f"[{self.name}] Error in _initialize value_type: {e}")
            self.value_type = None
        # print(f"[{self.name}] value_type: {self.value_type}")
        self.sub_key = self.obj.subscribe(self._stash_value, run=False)
        initial_value = self._get_value(check_connection=False)
        self._stash_value(initial_value)
        # print(f"[{self.name}] Initial value: {initial_value}")
        QTimer.singleShot(5000, self._check_value)
        # print(f"[{self.name}] PVModelRO Initialized")
        return True

    def _cleanup(self):
        self.obj.unsubscribe(self.sub_key)

    @requires_connection
    def _get_value(self):
        return self.obj.get(connection_timeout=0.2, timeout=0.2)

    def _check_value(self):
        value = self._get_value()
        self._stash_value(value)
        QTimer.singleShot(10000, self._check_value)

    def _value_changed(self, value, print_value=False, **kwargs):
        """Handle value changes, with better type handling."""
        # print(f"[{self.name}] _value_changed: {value}")
        if value is None:
            if self._value is None:
                return
            else:
                self._value = None
                self.valueChanged.emit(self._value)
                return

        try:
            # Extract value from named tuple if needed
            if hasattr(value, "_fields"):
                if hasattr(value, "user_readback"):
                    value = value.user_readback
                elif hasattr(value, "readback"):
                    value = value.readback
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
                print(f"[{self.name}] new value_type: {self.value_type}")

            # Format based on type
            if self.value_type is float:
                formatted_value = formatFloat(value)
            elif self.value_type is int:
                formatted_value = formatInt(value)
            else:
                formatted_value = str(value)
            if print_value:
                print(f"[{self.name}] value changed to {formatted_value}")

            if self._value != formatted_value:
                self._value = formatted_value
                self.valueChanged.emit(formatted_value)
        except Exception as e:
            print(f"[{self.name}] Error in _value_changed for value {value}: {e}")
            self._value = str(value)
            self.valueChanged.emit(str(value))

    @property
    def value(self):
        return self._value


class PVModel(PVModelRO):
    default_controller = PVControl

    @requires_connection
    def set(self, val):
        """Set the value of the PV, with type validation.

        Parameters
        ----------
        val : any
            Value to set. Must be compatible with the model's value_type.

        Raises
        ------
        ValueError
            If the value cannot be converted to the model's value_type.
        """
        if self.value_type is not None:
            try:
                converted_val = self.value_type(val)
            except (ValueError, TypeError) as e:
                type_name = self.value_type.__name__
                msg = f"Value {val} cannot be converted to type {type_name}"
                raise ValueError(msg) from e
            self.obj.set(converted_val).wait()
            return val
        else:
            self.obj.set(val).wait()
            return val


class EnumModel(PVModel):
    default_controller = EnumControl
    default_monitor = EnumMonitor

    enumChanged = Signal(tuple)

    def __init__(self, name, obj, group, long_name, **kwargs):
        self._enum_strs = tuple("")
        self._index_value = 0
        super().__init__(name, obj, group, long_name, **kwargs)
        EnumModel._initialize(self)

    @initialize_with_retry
    def _initialize(self):
        # print(f"Initializing EnumModel for {self.name}")
        if not super()._initialize():
            return False

        if hasattr(self.obj, "enum_strs") and self.obj.enum_strs is not None:
            self._enum_strs = tuple(self.obj.enum_strs)
            self.enumChanged.emit(self._enum_strs)
        else:
            print(
                f"Warning: {self.name} does not have enum_strs attribute or it is None."
            )
        return True

    @property
    def enum_strs(self):
        return self._enum_strs

    @requires_connection
    def set(self, value):
        if isinstance(value, str):
            if value in self._enum_strs:
                index = self._enum_strs.index(value)
                self.obj.set(index).wait()
            else:
                raise ValueError(f"{value} is not a valid option for {self.name}")
        elif isinstance(value, int):
            if 0 <= value < len(self._enum_strs):
                self.obj.set(value).wait()
            else:
                raise ValueError(f"{value} is not a valid index for {self.name}")
        else:
            raise TypeError("Value must be a string or integer")
        return value

    def _value_changed(self, value, **kwargs):
        if isinstance(value, int) and 0 <= value < len(self._enum_strs):
            self._index_value = value
            value = self._enum_strs[value]
        elif value in self._enum_strs:
            index = self._enum_strs.index(value)
            self._index_value = index
        self._value = str(value)
        self.valueChanged.emit(self._value)
