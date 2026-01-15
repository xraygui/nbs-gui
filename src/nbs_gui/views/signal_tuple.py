from qtpy.QtWidgets import QVBoxLayout, QGroupBox, QWidget

from .views import AutoMonitor, AutoControl


class SignalTupleBox(QWidget):
    """Group box wrapper for a collection of signal models."""

    def __init__(self, model, parent_model=None, title=None, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.parent_model = parent_model
        box_title = title if title is not None else model.label
        self.group = QGroupBox(box_title)
        self.layout = QVBoxLayout()
        self.group.setLayout(self.layout)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.group)
        self.setLayout(outer)


class SignalTupleMonitor(SignalTupleBox):
    def __init__(self, model, parent_model=None, title=None, **kwargs):
        super().__init__(model, parent_model=parent_model, title=title, **kwargs)
        for sig_model in model.signals:
            self.layout.addWidget(AutoMonitor(sig_model, parent_model))


class SignalTupleControl(SignalTupleBox):
    def __init__(self, model, parent_model=None, title=None, **kwargs):
        super().__init__(model, parent_model=parent_model, title=title, **kwargs)
        for sig_model in model.signals:
            self.layout.addWidget(AutoControl(sig_model, parent_model))


def MaybeTupleMonitor(self, model, parent_model=None, title=None, **kwargs):
    """Return a single PV widget if one signal, else a grouped box."""
    signals = getattr(model, "signals", [])
    if len(signals) == 1:
        sig = signals[0]
        return AutoMonitor(sig, parent_model)
    return SignalTupleMonitor(model, parent_model=parent_model, title=title, **kwargs)

def MaybeTupleControl(self, model, parent_model=None, title=None, **kwargs):
    """Return a single PV widget if one signal, else a grouped box."""
    signals = getattr(model, "signals", [])
    if len(signals) == 1:
        sig = signals[0]
        return AutoControl(sig, parent_model)
    return SignalTupleControl(model, parent_model=parent_model, title=title, **kwargs)
