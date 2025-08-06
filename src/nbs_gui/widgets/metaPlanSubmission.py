"""
Meta-plan submission widget for creating plans that run other plans.
"""

from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QStackedWidget,
)
from nbs_gui.plans.base import PlanWidgetBase
from nbs_gui.plans.durationMetaPlan import DurationMetaPlan
from nbs_gui.plans.conditionMetaPlan import ConditionMetaPlan, UntilConditionMetaPlan


class MetaPlanSubmissionWidget(QWidget):
    """
    Widget for submitting meta-plans that run sequences of other plans.

    Provides a dropdown to select between different meta-plan types and
    manages the individual meta-plan widgets.
    """

    def __init__(self, model, parent=None):
        super().__init__(parent)
        print("[MetaPlanSubmission] Initializing widget")
        self.model = model
        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.action_dict = {}

        # Create meta-plan widgets
        self._create_meta_plan_widgets()

        print(f"[MetaPlanSubmission] Loaded {len(self.action_dict)} meta-plan widgets")
        self.action_widget = QStackedWidget(self)

        # Create and add the action selection combo box
        self.action_label = QLabel("Meta-Plan Type Selection", self)
        self.action_selection = QComboBox(self)
        self.submit_button = QPushButton("Add to Queue", self)
        self.submit_button.clicked.connect(self.submit_plan)
        self.submit_button.setEnabled(False)
        self.staging_button = QPushButton("Add to Staging", self)
        self.staging_button.clicked.connect(self.stage_plan)
        self.staging_button.setEnabled(False)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_plan)

        print("[MetaPlanSubmission] Adding widgets to stacked widget")
        for k, widget in self.action_dict.items():
            self.action_widget.addWidget(widget)
            self.action_selection.addItem(k)

        self.layout = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(self.action_label)
        h.addWidget(self.action_selection)
        h.addWidget(self.submit_button)
        h.addWidget(self.staging_button)
        h.addWidget(self.reset_button)
        self.layout.addLayout(h)
        self.layout.addWidget(self.action_widget)

        self.action_selection.currentIndexChanged.connect(
            self.on_action_selection_changed
        )
        self.action_widget.currentChanged.connect(self.update_plan_ready_connection)
        self.update_plan_ready_connection(self.action_widget.currentIndex())

    def _create_meta_plan_widgets(self):
        """Create the individual meta-plan widgets."""
        # Duration-based meta-plan
        print("[MetaPlanSubmission] Creating duration meta-plan widget")
        duration_widget = DurationMetaPlan(self.model, self)
        self.action_dict[duration_widget.display_name] = duration_widget

        # Condition-based meta-plan (while condition)
        print("[MetaPlanSubmission] Creating condition meta-plan widget")
        condition_widget = ConditionMetaPlan(self.model, self)
        self.action_dict[condition_widget.display_name] = condition_widget

        # Condition-based meta-plan (until condition)
        print("[MetaPlanSubmission] Creating until condition meta-plan widget")
        until_condition_widget = UntilConditionMetaPlan(self.model, self)
        self.action_dict[until_condition_widget.display_name] = until_condition_widget

    def on_action_selection_changed(self, index):
        """Handler for action selection changes."""
        selected_name = self.action_selection.currentText()
        self.action_widget.setCurrentIndex(index)

    def update_plan_ready_connection(self, index):
        """Update the connection to the plan_ready signal of the current widget."""
        # Disconnect previous widget
        if hasattr(self, "current_widget") and isinstance(
            self.current_widget, PlanWidgetBase
        ):
            try:
                self.current_widget.plan_ready.disconnect(self.submit_button.setEnabled)
                self.current_widget.plan_ready.disconnect(
                    self.staging_button.setEnabled
                )
            except TypeError:
                pass

        # Connect new widget
        self.current_widget = self.action_widget.widget(index)
        if isinstance(self.current_widget, PlanWidgetBase):
            self.current_widget.plan_ready.connect(self.submit_button.setEnabled)
            self.current_widget.plan_ready.connect(self.staging_button.setEnabled)
        else:
            print("[MetaPlanSubmission] Current widget is not a PlanWidgetBase")

        self.current_widget.check_plan_ready()

    def submit_plan(self):
        """Submit the current meta-plan to the main queue."""
        selected_widget = self.action_widget.currentWidget()
        selected_widget.submit_all_plans()

    def stage_plan(self):
        """Stage the current meta-plan."""
        selected_widget = self.action_widget.currentWidget()
        selected_widget.stage_all_plans()

    def reset_plan(self):
        """Reset the current meta-plan."""
        selected_widget = self.action_widget.currentWidget()
        selected_widget.reset()
