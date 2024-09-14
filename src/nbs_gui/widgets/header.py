from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSplitter
from qtpy.QtCore import Qt
from bluesky_widgets.qt.run_engine_client import (
    QtReManagerConnection,
    QtReEnvironmentControls,
    QtReExecutionControls,
    QtReStatusMonitor,
    QtReRunningPlan,
)
from .queueControl import QtReQueueControls
from .status import ProposalStatus
from .motor import BeamlineMotorBars


class Header(QWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        layout.addWidget(QtReManagerConnection(self.model.run_engine))
        layout.addWidget(QtReEnvironmentControls(self.model.run_engine))
        layout.addWidget(QtReQueueControls(self.model.run_engine))
        layout.addWidget(QtReExecutionControls(self.model.run_engine))
        # layout.addWidget(QtReStatusMonitor(self.model.run_engine))

        # splitter = QSplitter(Qt.Vertical)
        # layout.addWidget(splitter, 1)  # Give the splitter more space
        # vbox = QVBoxLayout()
        # layout.addLayout(vbox)
        running_plan = QtReRunningPlan(self.model.run_engine)
        running_motors = BeamlineMotorBars(self.model)
        layout.addWidget(running_motors)
        layout.addWidget(running_plan)

        # Set initial sizes
        # splitter.setSizes([200, 0])  # Adjust these values as needed

        # Make the splitter handle invisible
        # splitter.handle(1).setEnabled(False)
        # splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")

        self.setLayout(layout)
