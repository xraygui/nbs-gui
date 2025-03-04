from qtpy.QtCore import Signal, QTimer
from qtpy.QtWidgets import QWidget
import numpy as np

from ..views.monitors import PVMonitor, PVControl
from ..views.enums import EnumControl, EnumMonitor
from .mixins import ModeManagedModel


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


class BaseModel(QWidget, ModeManagedModel):
    default_controller = None
    default_monitor = PVMonitor
    connectionStatusChanged = Signal(bool)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__()
        self.name = name
        self.obj = obj
        self.group = group
        self.label = long_name
        self.enabled = True
        self._connected = True

        # Set common attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Try initial connection
        if hasattr(self.obj, "wait_for_connection"):
            try:
                self.obj.wait_for_connection(timeout=1)
            except Exception as e:
                print(f"{name} timed out waiting for connection: {e}")
                self._connected = False
                self.connectionStatusChanged.emit(False)

        self.destroyed.connect(lambda: self._cleanup)
        self.units = None

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

    def _handle_reconnection(self):
        """Handle successful reconnection."""
        if not self._connected:
            self._connected = True
            self.connectionStatusChanged.emit(True)

    @property
    def connected(self):
        """Whether the device is currently connected."""
        return self._connected


class PVModelRO(BaseModel):
    valueChanged = Signal(str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        if hasattr(obj, "metadata"):
            self.units = obj.metadata.get("units", None)
            print(f"{name} has units {self.units}")
        else:
            self.units = None
            print(f"{name} has no metadata")

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

        self._value = "Disconnected"
        self.sub_key = self.obj.subscribe(self._value_changed, run=True)
        QTimer.singleShot(5000, self._check_value)

    def _cleanup(self):
        self.obj.unsubscribe(self.sub_key)

    def _check_value(self):
        try:
            value = self.obj.get(connection_timeout=0.2, timeout=0.2)
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


class PVModel(PVModelRO):
    default_controller = PVControl

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
        self._enum_strs = tuple("")
        self._index_value = 0
        super().__init__(name, obj, group, long_name, **kwargs)
        self._get_enum_strs()

    def _get_enum_strs(self):
        if hasattr(self.obj, "enum_strs") and self.obj.enum_strs is not None:
            self._enum_strs = tuple(self.obj.enum_strs)
            self.enumChanged.emit(self._enum_strs)
        else:
            print(
                f"Warning: {self.name} does not have enum_strs attribute or it is None. Retrying in 5 seconds."
            )
            QTimer.singleShot(5000, self._get_enum_strs)

    @property
    def enum_strs(self):
        return self._enum_strs

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
