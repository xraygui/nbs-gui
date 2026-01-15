from .base import BaseModel
from .base import PVModel
from ..views.signal_tuple import SignalTupleMonitor, SignalTupleControl, MaybeTupleMonitor, MaybeTupleControl

class SignalTupleModel(BaseModel):
    """Wrapper model for a collection of signal models."""

    default_monitor = SignalTupleMonitor # set by beamline to SignalTupleMonitor
    default_controller = SignalTupleControl  # set by beamline to SignalTupleControl

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        names = getattr(obj, "component_names", []) or []
        self.signals = [PVModel(comp, getattr(obj, comp), group, f"{long_name}.{comp}") for comp in names]
        self.keys = list(names)

    def iter_models(self):
        """
        Yield contained signal models for traversal.

        Yields
        ------
        BaseModel
            Contained signal models.
        """
        yield from self.signals

class MaybeTupleModel(BaseModel):
    """Wrapper model for a collection of signal models."""

    default_monitor = MaybeTupleMonitor # set by beamline to SignalTupleMonitor
    default_controller = MaybeTupleControl  # set by beamline to SignalTupleControl

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        names = getattr(obj, "component_names", []) or []
        self.signals = [PVModel(comp, getattr(obj, comp), group, f"{long_name}.{comp}") for comp in names]
        self.keys = list(names)

    def iter_models(self):
        """
        Yield contained signal models for traversal.

        Yields
        ------
        BaseModel
            Contained signal models.
        """
        yield from self.signals
