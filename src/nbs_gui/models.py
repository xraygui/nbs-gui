from bluesky_widgets.qt.threading import FunctionWorker
from qtpy.QtCore import QObject, Signal, QTimer
from qtpy.QtWidgets import QWidget
from bluesky_queueserver_api import BFunc
from ophyd.signal import ConnectionTimeoutError
from ophyd.utils.errors import DisconnectedError
import time
import numpy as np

from .widgets.motor import MotorControl, MotorMonitor
from .widgets.monitors import PVMonitor, PVControl
from .widgets.enums import EnumControl, EnumMonitor
from .widgets.gatevalve import GVControl, GVMonitor
from .widgets.energy import EnergyControl, EnergyMonitor
from .widgets.manipulator_monitor import RealManipulatorControl, RealManipulatorMonitor


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


class UserStatus(QObject):
    def __init__(self, runEngineClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.REClientModel = runEngineClient
        self.REClientModel.events.status_changed.connect(self.on_status_update)
        self._signal_registry = {}
        self._uid_registry = {}
        self._item_cache = {}
        self._thread = None
        self.updates_activated = False
        self.update_period = 1

    def _start_thread(self):
        self._thread = FunctionWorker(self._reload_status)
        self._thread.finished.connect(self._reload_complete)
        self.updates_activated = True
        self._thread.start()

    def _reload_complete(self):
        if not self._deactivate_updates:
            self._start_thread()
        else:
            self.updates_activated = False
            self._deactivate_updates = False

    def get_update(self, key):
        function = BFunc("request_update", key)
        response = self.REClientModel._client.function_execute(
            function, run_in_background=True
        )
        self.REClientModel._client.wait_for_completed_task(response["task_uid"])
        reply = self.REClientModel._client.task_result(response["task_uid"])
        task_status = reply["status"]
        task_result = reply["result"]
        if task_status == "completed" and task_result.get("success", False):
            self._item_cache[key] = task_result["return_value"]
            return task_result["return_value"]
        else:
            raise ValueError("Update unsuccessful")

    def get_cached(self, key, default=None):
        return self._item_cache.get(key, default)

    def _reload_status(self):
        function = BFunc("get_status")
        response = self.REClientModel._client.function_execute(
            function, run_in_background=True
        )
        self.REClientModel._client.wait_for_completed_task(response["task_uid"])
        reply = self.REClientModel._client.task_result(response["task_uid"])
        task_status = reply["status"]
        task_result = reply["result"]
        if task_status == "completed" and task_result.get("success", False):
            user_status = task_result["return_value"]
        else:
            raise ValueError("Status did not load successfully")
        new_uids = {}

        for key, signal_list in self._signal_registry.items():
            new_uid = user_status.get(key, "")
            if new_uid != self._uid_registry.get(key, ""):
                update = self.get_update(key)
                for sig in signal_list:
                    sig.emit(update)
                new_uids[key] = new_uid
        self._uid_registry.update(new_uids)
        time.sleep(self.update_period)

    def register_signal(self, key, signal, emit_cached=True):
        if key in self._signal_registry:
            if signal not in self._signal_registry[key]:
                self._signal_registry[key].append(signal)
        else:
            self._signal_registry[key] = [signal]
        if emit_cached:
            value = self.get_cached(key)
            if value is not None:
                signal.emit(value)

    def on_status_update(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        worker_exists = status.get("worker_environment_exists", False)
        self._deactivate_updates = not is_connected or not worker_exists
        if not self._deactivate_updates and not self.updates_activated:
            self._start_thread()


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
            print(self.label, new_sp, self._setpoint, type(new_sp))
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
