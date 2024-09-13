from qtpy.QtWidgets import QWidget, QHBoxLayout
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


class Header(QWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        layout = QHBoxLayout()

        layout.addWidget(QtReManagerConnection(self.model.run_engine))
        layout.addWidget(QtReEnvironmentControls(self.model.run_engine))
        layout.addWidget(QtReQueueControls(self.model.run_engine))
        layout.addWidget(QtReExecutionControls(self.model.run_engine))
        layout.addWidget(QtReStatusMonitor(self.model.run_engine))
        #layout.addWidget(ProposalStatus(self.model.run_engine, self.model.user_status))

        running_plan = QtReRunningPlan(self.model.run_engine)
        # running_plan.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Preferred)
        layout.addWidget(
            running_plan, 1
        )  # The '1' argument gives this widget a stretch factor

        self.setLayout(layout)
