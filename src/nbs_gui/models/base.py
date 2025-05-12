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

CONNECTION_ERRORS = (
    ReadTimeoutError,
    DisconnectedError,
    ConnectionTimeoutError,
    StatusTimeoutError,
    ChannelAccessGetFailure,
)


def initialize_with_retry(func, retry_intervals=None):
    """
    Decorator for initialization methods that:
    1. Ensures method only runs once successfully
    2. Handles retrying failed initializations with exponential backoff
    3. Ensures parent class initialization succeeds first

    The decorated method should:
    1. Call super()._initialize() if it has a parent class
    2. Return True if initialization succeeded
    3. Return False if initialization failed

    Retry intervals:
    - 1st attempt: 1 second
    - 2nd attempt: 5 seconds
    - 3rd attempt: 30 seconds
    - 4th attempt: 60 seconds
    - 5th+ attempts: 120 seconds
    """
    RETRY_INTERVALS = retry_intervals or [1000, 30000, 60000, 120000]  # in milliseconds

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Initialize the set if it doesn't exist
        if not hasattr(self, "_initialized_methods"):
            self._initialized_methods = set()

        # Initialize retry counter if it doesn't exist
        if not hasattr(self, "_init_retry_counts"):
            self._init_retry_counts = {}

        # Get the qualified name for this initialization method
        qual_name = func.__qualname__

        # If this method has already been successfully initialized, skip
        if qual_name in self._initialized_methods:
            return True

        try:
            # Run the initialization method
            result = func(self, *args, **kwargs)

            # If successful, mark as initialized and reset retry counter
            if result:
                self._initialized_methods.add(qual_name)
                if qual_name in self._init_retry_counts:
                    del self._init_retry_counts[qual_name]
                return True
            else:
                # Get current retry count and increment
                retry_count = self._init_retry_counts.get(qual_name, 0)
                self._init_retry_counts[qual_name] = retry_count + 1

                # Get retry interval (use last interval if we've exceeded the list)
                interval = RETRY_INTERVALS[min(retry_count, len(RETRY_INTERVALS) - 1)]

                # Schedule retry
                print(
                    f"Initialization failed for {self.name}.{func.__name__}, "
                    f"attempt {retry_count + 1}, retrying in {interval/1000}s"
                )
                QTimer.singleShot(interval, lambda: wrapper(self, *args, **kwargs))
                return False

        except Exception as e:
            # Handle exceptions same as failed initialization
            print(f"Initialization failed for {qual_name}: {e}")

            retry_count = self._init_retry_counts.get(qual_name, 0)
            self._init_retry_counts[qual_name] = retry_count + 1
            interval = RETRY_INTERVALS[min(retry_count, len(RETRY_INTERVALS) - 1)]

            print(
                f"Retrying {self.name}.{func.__name__} after error, "
                f"attempt {retry_count + 1}, in {interval/1000}s"
            )
            QTimer.singleShot(interval, lambda: wrapper(self, *args, **kwargs))
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
    except (ValueError, TypeError):
        return str(value)  # Return as string if conversion fails


def requires_connection(func):
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
    def wrapper(self, *args, **kwargs):
        if not self.connected:
            print(f"Device {self.name} not connected for {func.__name__}")
            # Let _check_connection handle reconnection logic
            self._check_connection()
            return None

        try:
            return func(self, *args, **kwargs)
        except CONNECTION_ERRORS as e:
            print(f"Connection error in {func.__name__} for {self.name}: {e}")
            # Let _check_connection handle reconnection logic
            self._check_connection()
            return None

    return wrapper


class BaseModel(QWidget, ModeManagedModel):
    default_controller = None
    default_monitor = PVMonitor
    connectionStatusChanged = Signal(bool)

    def __init__(self, name, obj, group, long_name, **kwargs):
        print(f"Initializing BaseModel for {name}")
        super().__init__()
        self.name = name
        self.obj = obj
        self.group = group
        self.label = long_name
        self.enabled = True
        self._connected = False  # Start as disconnected
        self._value = "Disconnected"
        # Create reconnection timer
        self._reconnection_timer = QTimer()
        self._reconnection_timer.timeout.connect(self._check_connection)
        self._reconnection_timer.setSingleShot(True)

        # Set common attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Try initial connection
        self._initialize()

        self.destroyed.connect(lambda: self._cleanup)
        self.units = None
        print(f"Initialized BaseModel for {name}")

    @initialize_with_retry
    def _initialize(self):
        """Base initialization"""
        print(f"Initializing BaseModel for {self.name}")

        return self._check_connection(retry_on_failure=False)

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

    def _check_connection(self, retry_on_failure=True):
        """
        Check connection and handle reconnection attempts.
        All connection checking and reconnection logic lives here.
        """

        try:
            if hasattr(self.obj, "wait_for_connection"):
                self.obj.wait_for_connection(timeout=0.2)
                connected = True
            else:
                self.obj.get(timeout=0.2)
                connected = True
        except CONNECTION_ERRORS:
            connected = False

        # Update connection state if changed
        if connected != self._connected:
            self._connected = connected
            self.connectionStatusChanged.emit(connected)

            # If we're now connected, try initialization
            if not connected and retry_on_failure:
                if not self._reconnection_timer.isActive():
                    print(f"Starting reconnection timer for {self.name}")
                    self._reconnection_timer.start(60000)

        return connected

    @property
    def connected(self):
        """Whether the device is currently connected."""
        return self._connected


class PVModelRO(BaseModel):
    valueChanged = Signal(str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        print(f"Initializing PVModelRO for {name}")
        self._initialize()

    @initialize_with_retry
    def _initialize(self):
        print(f"Initializing PVModelRO for {self.name}")
        if not super()._initialize():
            self.value_type = None
            self.units = None
            return False

        if hasattr(self.obj, "metadata"):
            self.units = self.obj.metadata.get("units", None)
            print(f"{self.name} has units {self.units}")
        else:
            self.units = None
            print(f"{self.name} has no metadata")

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
        except:
            self.value_type = None

        self.sub_key = self.obj.subscribe(self._value_changed, run=False)
        QTimer.singleShot(5000, self._check_value)
        print(f"Initialized PVModelRO for {self.name}")
        return True

    def _cleanup(self):
        self.obj.unsubscribe(self.sub_key)

    @requires_connection
    def _check_value(self):
        value = self.obj.get(connection_timeout=0.2, timeout=0.2)
        self._value_changed(value)
        QTimer.singleShot(100000, self._check_value)

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
        else:
            self.obj.set(val).wait()


class EnumModel(PVModel):
    default_controller = EnumControl
    default_monitor = EnumMonitor

    enumChanged = Signal(tuple)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self._initialize()

    @initialize_with_retry
    def _initialize(self):
        print(f"Initializing EnumModel for {self.name}")
        self._enum_strs = tuple("")
        self._index_value = 0
        if not super()._initialize():
            return False

        if hasattr(self.obj, "enum_strs") and self.obj.enum_strs is not None:
            self._enum_strs = tuple(self.obj.enum_strs)
            self.enumChanged.emit(self._enum_strs)
        else:
            print(
                f"Warning: {self.name} does not have enum_strs attribute or it is None."
            )

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

    def _value_changed(self, value, **kwargs):
        if isinstance(value, int) and 0 <= value < len(self._enum_strs):
            self._index_value = value
            value = self._enum_strs[value]
        elif value in self._enum_strs:
            index = self._enum_strs.index(value)
            self._index_value = index
        self._value = str(value)
        self.valueChanged.emit(self._value)
