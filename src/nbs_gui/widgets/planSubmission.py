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
    QFileDialog,
    QMessageBox,
)
from ..plans.planLoaders import PlanLoaderWidgetBase
from ..plans.base import PlanWidgetBase


class PlanSubmissionWidget(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        print("[PlanSubmission] Initializing widget")
        self.model = model
        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.action_dict = {}
        config = model.settings.gui_config

        plans_to_include = config.get("gui", {}).get("plans", {}).get("include", [])
        plans_to_exclude = config.get("gui", {}).get("plans", {}).get("exclude", [])
        explicit_inclusion = len(plans_to_include) > 0

        plans = pkg_resources.iter_entry_points("nbs_gui.plans")
        print("[PlanSubmission] Loading plan entry points")
        for plan_entry_point in plans:
            if explicit_inclusion:
                if plan_entry_point.name in plans_to_include:
                    print(
                        f"[PlanSubmission] Loading included plan: {plan_entry_point.name}"
                    )
                    plan = plan_entry_point.load()
                    if callable(plan):
                        plan_widget = plan(model, self)
                        display_name = getattr(
                            plan_widget, "display_name", plan_entry_point.name
                        )
                        print(f"[PlanSubmission] Created widget for {display_name}")
                        self.action_dict[display_name] = plan_widget
            elif plan_entry_point.name not in plans_to_exclude:
                print(
                    f"[PlanSubmission] Loading non-excluded plan: {plan_entry_point.name}"
                )
                plan = plan_entry_point.load()
                if callable(plan):
                    plan_widget = plan(model, self)
                    display_name = getattr(
                        plan_widget, "display_name", plan_entry_point.name
                    )
                    print(f"[PlanSubmission] Created widget for {display_name}")
                    self.action_dict[display_name] = plan_widget

        print(f"[PlanSubmission] Loaded {len(self.action_dict)} plan widgets")
        self.action_widget = QStackedWidget(self)

        # Create and add the action selection combo box
        self.action_label = QLabel("Plan Type Selection", self)
        self.action_selection = QComboBox(self)
        self.submit_button = QPushButton("Add to Queue", self)
        self.submit_button.clicked.connect(self.submit_plan)
        self.submit_button.setEnabled(False)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_plan)

        print("[PlanSubmission] Adding widgets to stacked widget")
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
        self.layout.addWidget(self.action_widget)

        self.action_selection.currentIndexChanged.connect(
            self.on_action_selection_changed
        )
        self.action_widget.currentChanged.connect(self.update_plan_ready_connection)
        self.update_plan_ready_connection(self.action_widget.currentIndex())

    def on_action_selection_changed(self, index):
        """Handler for action selection changes"""
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
            except TypeError:
                pass

        # Connect new widget
        self.current_widget = self.action_widget.widget(index)
        if isinstance(self.current_widget, PlanWidgetBase):
            self.current_widget.plan_ready.connect(self.submit_button.setEnabled)
        else:
            print("[PlanSubmission] Current widget is not a PlanWidgetBase")

        self.current_widget.check_plan_ready()

    def submit_plan(self):
        selected_widget = self.action_widget.currentWidget()
        selected_widget.submit_all_plans()

    def reset_plan(self):
        selected_widget = self.action_widget.currentWidget()
        selected_widget.reset()


class PlanLoadWidget(QWidget):

    def __init__(self, model, parent=None):
        super().__init__(parent)
        print("Initializing PlanLoadWidget")
        self.model = model
        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.action_dict = {}
        config = model.settings.gui_config

        plans_to_include = (
            config.get("gui", {}).get("plan_loaders", {}).get("include", [])
        )
        plans_to_exclude = (
            config.get("gui", {}).get("plan_loaders", {}).get("exclude", [])
        )
        explicit_inclusion = len(plans_to_include) > 0

        plans = pkg_resources.iter_entry_points("nbs_gui.plan_loaders")
        # Need to load only desired plans from config file!
        for plan_entry_point in plans:
            if explicit_inclusion:
                if plan_entry_point.name in plans_to_include:
                    print(f"Initializing {plan_entry_point.name} Loader")
                    plan = plan_entry_point.load()  # Load the modifier function
                    if callable(plan):
                        # Call the modifier function with model and self (as parent) to get the QWidget
                        plan_widget = plan(model, self)
                        print("Created plan loader")
                        self.action_dict[
                            getattr(plan_widget, "display_name", plan_entry_point.name)
                        ] = plan_widget
                        print("Added plan loader to dict")
            elif plan_entry_point.name not in plans_to_exclude:
                print(f"Initializing {plan_entry_point.name}")
                plan = plan_entry_point.load()  # Load the modifier function
                if callable(plan):
                    # Call the modifier function with model and self (as parent) to get the QWidget
                    plan_widget = plan(model, self)
                    self.action_dict[
                        getattr(plan_widget, "display_name", plan_entry_point.name)
                    ] = plan_widget
        print("Initialized Loader Dict")
        self.action_widget = QStackedWidget(self)

        # Create and add the action selection combo box
        self.action_label = QLabel("Load Type", self)
        self.action_selection = QComboBox(self)
        self.file_picker_button = QPushButton("Choose File", self)
        self.file_picker_button.clicked.connect(self.pick_file)
        self.reset_button = QPushButton("Reset", self)
        self.reset_button.clicked.connect(self.reset_plan)

        for k, widget in self.action_dict.items():
            self.action_widget.addWidget(widget)
            self.action_selection.addItem(k)

        self.layout = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(self.action_label)
        h.addWidget(self.action_selection)
        h.addWidget(self.file_picker_button)
        h.addWidget(self.reset_button)
        self.layout.addLayout(h)
        print("Loaders Added")

        self.layout.addWidget(self.action_widget)
        print("Modifier Added")

        # Create and add the submit button
        self.submit_button = QPushButton("Submit Plan Queue", self)
        self.submit_button.clicked.connect(self.submit_plan)
        self.layout.addWidget(self.submit_button)
        print("Submit Button Added")
        self.action_selection.currentIndexChanged.connect(
            self.action_widget.setCurrentIndex
        )
        self.action_widget.currentChanged.connect(self.update_plan_ready_connection)
        self.update_plan_ready_connection(self.action_widget.currentIndex())
        print("Finished PlanLoadWidget")

    def update_plan_ready_connection(self, index):
        """
        Update the connection to the plan_ready signal of the current widget.
        """
        print("Updating PlanLoad plan ready connection")
        # Disconnect the plan_ready signal of the previous widget
        if hasattr(self, "current_widget") and isinstance(
            self.current_widget, PlanLoaderWidgetBase
        ):
            try:
                self.current_widget.plan_ready.disconnect(self.submit_button.setEnabled)
            except TypeError:
                # The signal was not connected
                pass

        # Connect the plan_ready signal of the new widget
        self.current_widget = self.action_widget.widget(index)
        if isinstance(self.current_widget, PlanLoaderWidgetBase):
            self.current_widget.plan_ready.connect(self.submit_button.setEnabled)
        print("Checking if PlanLoadWidget is ready")

        self.current_widget.check_plan_ready()

    def submit_plan(self):
        # Get the selected action, noun, and modifier
        selected_widget = self.action_widget.currentWidget()
        selected_widget.submit_all_plans()

    def reset_plan(self):
        # Get the selected action, noun, and modifier
        selected_widget = self.action_widget.currentWidget()
        selected_widget.clear_plan_queue()

    def pick_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Choose CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )
        if file_name:
            selected_widget = self.action_widget.currentWidget()
            try:
                selected_widget.load_plan_file(file_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error generating queue: {str(e)}")
