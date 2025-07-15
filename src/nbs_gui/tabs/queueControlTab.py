from qtpy.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QSplitter
from qtpy.QtCore import Qt
from ..widgets.planSubmission import PlanSubmissionWidget, PlanLoadWidget
from ..widgets.planEditor import PlanEditor
from ..widgets.simpleConsoleMonitor import QtReConsoleMonitor
from ..widgets.QtReQueueStaging import QtReQueueStaging
from ..widgets.metaPlanSubmission import MetaPlanSubmissionWidget
from ..widgets.QtRePlanQueueBase import QtRePlanQueue, QtRePlanHistory

# from ..widgets.plan_creator import QtRePlanEditor


class QueueControlTab(QWidget):
    name = "Queue Control"

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model.run_engine
        main_layout = QVBoxLayout()

        vertical_splitter = QSplitter(Qt.Vertical)

        horizontal_splitter = QSplitter(Qt.Horizontal)

        pe = PlanEditor(model)
        if (
            model.settings.gui_config.get("gui", {})
            .get("plans", {})
            .get("load_plans", True)
        ):
            ps = PlanSubmissionWidget(model, self)
            pl = PlanLoadWidget(model, self)
            pe._tab_widget.addTab(ps, "Plan Widgets")
            pe._tab_widget.addTab(pl, "Plan Loaders")

        # Add MetaPlanSubmissionWidget tab
        mps = MetaPlanSubmissionWidget(model, self)
        pe._tab_widget.addTab(mps, "Meta Plan Widget")

        horizontal_splitter.addWidget(pe)

        tab_widget = QTabWidget()
        print("DEBUG: QueueControlTab - model")
        pq = QtRePlanQueue(model)
        print("DEBUG: QueueControlTab - pq created")
        ph = QtRePlanHistory(model)
        print("DEBUG: QueueControlTab - ph created")
        qs = QtReQueueStaging(model)
        print("DEBUG: QueueControlTab - qs created")
        pq.registered_item_editors.append(pe.edit_queue_item)
        qs.registered_item_editors.append(pe.edit_staged_item)

        tab_widget.addTab(pq, "Plan Queue")
        tab_widget.addTab(ph, "Plan History")
        tab_widget.addTab(qs, "Queue Staging")
        horizontal_splitter.addWidget(tab_widget)

        vertical_splitter.addWidget(horizontal_splitter)
        vertical_splitter.addWidget(QtReConsoleMonitor(self.model))

        main_layout.addWidget(vertical_splitter)
        self.setLayout(main_layout)
