from qtpy.QtCore import Signal, QTimer
from qtpy.QtWidgets import QWidget
import numpy as np

from ..widgets.monitors import PVMonitor, PVControl
from ..widgets.enums import EnumControl, EnumMonitor


def formatFloat(value, precision=2):
    if np.abs(value) >= 10 ** (1 - precision):
        fmtstr = f"{{:.{precision}f}}"
    elif value == 0:
        fmtstr = f"{{:.{precision}f}}"
    else:
        fmtstr = f"{{:.{precision}e}}"
    valueStr = fmtstr.format(value)
    return valueStr


def formatInt(value):
    valueStr = "{:d}".format(value)
    return valueStr


class BaseModel(QWidget):
    default_controller = None
    default_monitor = PVMonitor

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__()
        self.name = name
        self.obj = obj
        if hasattr(self.obj, "wait_for_connection"):
            try:
                self.obj.wait_for_connection(timeout=1)
            except:
                print(f"{name} timed out waiting for connection, moving on!")
        self.group = group
        self.label = long_name
        self.enabled = True
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.destroyed.connect(lambda: self._cleanup)
        self.units = None

    def _cleanup(self):
        pass


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

        self.value_type = None
        self._value = "Disconnected"
        self.sub_key = self.obj.subscribe(self._value_changed, run=True)
        timer = QTimer.singleShot(5000, self._check_value)

    def _cleanup(self):
        self.obj.unsubscribe(self.sub_key)

    def _check_value(self):
        try:
            value = self.obj.get(connection_timeout=0.2, timeout=0.2)
            # print(f"Time check value for {self.label}: {value}")
            self._value_changed(value)
            QTimer.singleShot(100000, self._check_value)
        except:
            QTimer.singleShot(10000, self._check_value)

    def _value_changed(self, value, **kwargs):
        # print(f"{self.label} got {value}, with type {self.value_type}")
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
        self._value = value
        # print(f"Emitting {value}")
        self.valueChanged.emit(value)

    @property
    def value(self):
        return self._value


class PVModel(PVModelRO):
    default_controller = PVControl
    # Need to make this more robust!

    def set(self, val):
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
