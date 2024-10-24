import pkg_resources
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QSizePolicy,
)
from bluesky_widgets.qt.run_engine_client import (
    QtRePlanQueue,
    # QtReQueueControls,
    QtReExecutionControls,
)
from ..widgets.queueControl import QtReQueueControls
from ..plans.base import PlanWidgetBase
from ..settings import SETTINGS


class PlanTabWidget(QWidget):
    name = "Plan Editor"

    def __init__(self, model, parent=None):
        print("Initializing PlanTab")
        super().__init__(parent)

        layout = QVBoxLayout()
        # Create and add the PlanSubmissionWidget
        submissionBox = QHBoxLayout()
        self.plan_submission_widget = PlanSubmissionWidget(model, self)
        submissionBox.addWidget(self.plan_submission_widget)
        submissionBox.addWidget(QtReQueueControls(model.run_engine))
        submissionBox.addWidget(QtReExecutionControls(model.run_engine))

        # self.plan_submission_widget.setParent(self)
        layout.addLayout(submissionBox)

        # Create and add the _QtReViewer
        self.qt_plan_queue = QtRePlanQueue(model.run_engine)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)

        self.qt_plan_queue.setSizePolicy(sizePolicy)
        layout.addWidget(self.qt_plan_queue)
        self.setLayout(layout)
        print("Finished Initializing PlanTab")


class PlanSubmissionWidget(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        print("Initializing PlanSubmission")
        self.model = model
        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.action_dict = {}
        config = SETTINGS.gui_config

        plans_to_include = config.get("gui", {}).get("plans", {}).get("include", [])
        plans_to_exclude = config.get("gui", {}).get("plans", {}).get("exclude", [])
        explicit_inclusion = len(plans_to_include) > 0

        plans = pkg_resources.iter_entry_points("nbs_gui.plans")
        # Need to load only desired plans from config file!
        for plan_entry_point in plans:
            if explicit_inclusion:
                if plan_entry_point.name in plans_to_include:
                    print(f"Initializing {plan_entry_point.name}")
                    plan = plan_entry_point.load()  # Load the modifier function
                    if callable(plan):
                        # Call the modifier function with model and self (as parent) to get the QWidget
                        plan_widget = plan(model, self)
                        print("Created plan_widget")
                        self.action_dict[
                            getattr(plan_widget, "display_name", plan_entry_point.name)
                        ] = plan_widget
                        print("Added Plan Widget to dict")
            elif plan_entry_point.name not in plans_to_exclude:
                print(f"Initializing {plan_entry_point.name}")
                plan = plan_entry_point.load()  # Load the modifier function
                if callable(plan):
                    # Call the modifier function with model and self (as parent) to get the QWidget
                    plan_widget = plan(model, self)
                    self.action_dict[
                        getattr(plan_widget, "display_name", plan_entry_point.name)
                    ] = plan_widget
        print("Initialized Action Dict")
        self.action_widget = QStackedWidget(self)

        # Create and add the action selection combo box
        self.action_label = QLabel("Plan Type Selection", self)
        self.action_selection = QComboBox(self)
        self.submit_button = QPushButton("Add to Queue", self)
        self.submit_button.clicked.connect(self.submit_plan)
        self.submit_button.setEnabled(False)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_plan)

        for k, widget in self.action_dict.items():
            self.action_widget.addWidget(widget)
            self.action_selection.addItem(k)

        self.layout = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(self.action_label)
        h.addWidget(self.action_selection)
        h.addWidget(self.submit_button)
        h.addWidget(self.reset_button)
        self.layout.addLayout(h)
        print("Actions Added")
        # Create and add the default modifier selection combo box
        self.layout.addWidget(self.action_widget)
        print("Modifier Added")

        # Update the modifier selection options based on the selected action
        self.action_selection.currentIndexChanged.connect(
            self.action_widget.setCurrentIndex
        )
        # Create and add the submit button
        self.action_widget.currentChanged.connect(self.update_plan_ready_connection)
        self.update_plan_ready_connection(self.action_widget.currentIndex())
        print("Finished PlanSubmission")

    def update_plan_ready_connection(self, index):
        """
        Update the connection to the plan_ready signal of the current widget.
        """
        # Disconnect the plan_ready signal of the previous widget
        if hasattr(self, "current_widget") and isinstance(
            self.current_widget, PlanWidgetBase
        ):
            try:
                self.current_widget.plan_ready.disconnect(self.submit_button.setEnabled)
            except TypeError:
                # The signal was not connected
                pass

        # Connect the plan_ready signal of the new widget
        self.current_widget = self.action_widget.widget(index)
        if isinstance(self.current_widget, PlanWidgetBase):
            self.current_widget.plan_ready.connect(self.submit_button.setEnabled)
        self.current_widget.check_plan_ready()

    def submit_plan(self):
        # Get the selected action, noun, and modifier
        selected_widget = self.action_widget.currentWidget()
        selected_widget.submit_plan()

    def reset_plan(self):
        # Get the selected action, noun, and modifier
        selected_widget = self.action_widget.currentWidget()
        selected_widget.reset()
