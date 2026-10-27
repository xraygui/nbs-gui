from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qtpy.QtCore import Qt
from ..widgets.utils import ByteIndicator


class BeamStatusMonitor(QWidget):
    """
    Widget to monitor a BeamStatusModel: whether beam is expected at the
    endstation, and the reason when it is not.
    """

    def __init__(self, model, parent_model=None, orientation="h", **kwargs):
        super().__init__(**kwargs)
        print(f"Initializing BeamStatusMonitor for model: {model.label}")
        self.model = model

        vbox = QVBoxLayout()
        vbox.setContentsMargins(2, 1, 2, 1)
        vbox.setSpacing(2)

        hbox = QHBoxLayout()
        hbox.setSpacing(4)
        node = model.node_name or "endstation"
        self.label = QLabel(f"Beam at {node}")
        self.indicator = ByteIndicator()
        self.indicator.setFixedSize(15, 15)
        self.status = QLabel("Unknown")
        hbox.addWidget(self.label)
        hbox.addStretch()
        hbox.addWidget(self.indicator)
        hbox.addWidget(self.status)
        vbox.addLayout(hbox)

        self.reason = QLabel("")
        self.reason.setWordWrap(True)
        self.reason.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.reason.setVisible(False)
        vbox.addWidget(self.reason)
        vbox.addStretch()

        self.setLayout(vbox)
        self.model.beamStatusChanged.connect(self.update_status)
        self.update_status(model.beam_expected, model.reason)

    def update_status(self, expected, reason):
        if expected is None:
            self.indicator.setColor("grey")
            self.status.setText("Unknown")
        elif expected:
            self.indicator.setColor("green")
            self.status.setText("Expected")
        else:
            self.indicator.setColor("red")
            self.status.setText("Not expected")
        show_reason = expected is not True and bool(reason)
        self.reason.setText(reason if show_reason else "")
        self.reason.setVisible(show_reason)
