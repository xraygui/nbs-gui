from qtpy.QtCore import Signal

from ..views.beam_status import BeamStatusMonitor
from .base import BaseModel, initialize_with_retry


class BeamStatusModel(BaseModel):
    """
    Beam status at one node of an nbs_bl BeamMap device: whether beam is
    expected there, and why not.

    The node defaults to the map's endstation. Load it for a BeamMap device
    from gui_config.toml::

        [loaders]
        "BeamMapFactory" = "nbs_gui.models.BeamStatusModel"

    and put it in the "signals" group to show it in the monitor tab.
    """

    default_monitor = BeamStatusMonitor
    view_only = True
    beamStatusChanged = Signal(object, str)

    def __init__(self, name, obj, group, long_name, **kwargs):
        super().__init__(name, obj, group, long_name, **kwargs)
        self.node_name = getattr(self.obj, "endstation", None)
        self.beam_expected = None
        self.reason = ""
        self._subs = []
        BeamStatusModel._initialize(self)

    @initialize_with_retry
    def _initialize(self):
        if not super()._initialize():
            return False
        node = self.obj.nodes.get(self.node_name) if self.node_name else None
        if node is None:
            self.reason = "No endstation set in the beam map"
            self._has_update = True
            return True
        self._subs = [
            (node.beam_expected, node.beam_expected.subscribe(self._expected_changed)),
            (node.reason, node.reason.subscribe(self._reason_changed)),
        ]
        return True

    def _cleanup(self):
        for signal, key in self._subs:
            signal.unsubscribe(key)
        self._subs = []

    def _expected_changed(self, value=None, **kwargs):
        self.beam_expected = None if value is None else bool(value)
        self._has_update = True

    def _reason_changed(self, value=None, **kwargs):
        self.reason = "" if value is None else str(value)
        self._has_update = True

    def _value_changed(self, value, **kwargs):
        # Called from drain_pending on the GUI thread; the subscription
        # callbacks above only record the latest values.
        self.beamStatusChanged.emit(self.beam_expected, self.reason)
