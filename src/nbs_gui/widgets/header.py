from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from .QtReRunningPlan import QtReRunningPlan
from .queueControl import QtReQueueControls, QtReStatusMonitor
from .serverControl import QueueServerControls
from .planControl import PlanControls
from ..views.motor import BeamlineMotorBars
from ..views.status import StatusBox


class MinimalHeader(QWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Replace separate connection and environment controls with combined widget
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(1)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        hbox.addWidget(QueueServerControls(self.model.run_engine))
        hbox.addWidget(QtReQueueControls(self.model.run_engine))
        hbox.addWidget(PlanControls(self.model.run_engine))
        vbox.addWidget(QtReStatusMonitor(self.model.run_engine))
        vbox.addLayout(hbox)

        # vbox.addLayout(hbox)
        layout.addLayout(vbox)
        running_plan = QtReRunningPlan(self.model)

        layout.addWidget(running_plan)

        self.setLayout(layout)


class Header(QWidget):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Replace separate connection and environment controls with combined widget
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(1)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        hbox.addWidget(QueueServerControls(self.model.run_engine))
        hbox.addWidget(QtReQueueControls(self.model.run_engine))
        hbox.addWidget(PlanControls(self.model.run_engine))
        vbox.addWidget(QtReStatusMonitor(self.model.run_engine))
        vbox.addLayout(hbox)

        # vbox.addLayout(hbox)
        layout.addLayout(vbox)
        layout.addWidget(BeamlineMotorBars(self.model))
        running_plan = QtReRunningPlan(self.model)
        layout.addWidget(running_plan)

        self.setLayout(layout)
