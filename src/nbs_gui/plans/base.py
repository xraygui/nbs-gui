from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QCheckBox,
    QPushButton,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator, QColor, QPalette
from qtpy.QtCore import Signal, Qt
from typing import Any
from .planParam import AutoParamGroup


class PlanWidgetBase(QWidget):
    """
    Base class for plan widgets providing essential functionality.

    Parameters
    ----------
    model : object
        The model object containing run_engine and user_status
    parent : QWidget, optional
        Parent widget
    """

    widget_updated = Signal()
    plan_ready = Signal(bool)
    editingFinished = Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.layout = QVBoxLayout(self)

    def _check_ready(self):
        """
        Check if all parameters are ready.

        Returns
        -------
        bool
            True if all parameters are ready, False otherwise
        """
        raise NotImplementedError

    def check_plan_ready(self):
        """
        Check if all parameters are ready and emit plan_ready signal.
        """
        self.plan_ready.emit(self._check_ready())

    def reset(self):
        raise NotImplementedError

    def submit_plan(self, item):
        """
        Submit a plan item to the run engine client.

        Parameters
        ----------
        item : BPlan
            The plan item to be submitted

        Returns
        -------
        bool
            True if submission was successful, False otherwise
        """
        try:
            self.run_engine_client.queue_item_add(item=item)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Submission Error",
                f"Failed to submit plan: {str(e)}",
                QMessageBox.Ok,
            )
            return False

    def create_plan_items(self):
        """
        Create and return a list of plan items to be submitted.

        Returns
        -------
        list
            A list of BPlan items to be submitted
        """
        raise NotImplementedError("This method should be implemented by child classes.")

    def submit_all_plans(self):
        """
        Create and submit all plan items.
        """
        plan_items = self.create_plan_items()
        for item in plan_items:
            if not self.submit_plan(item):
                break

    def stage_plan(self, item):
        """
        Stage a plan item.
        """
        try:
            self.model.queue_staging.queue_item_add(item=item)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Staging Error",
                f"Failed to stage plan: {str(e)}",
                QMessageBox.Ok,
            )
            return False

    def stage_all_plans(self):
        """
        Create and stage all plan items.
        """
        plan_items = self.create_plan_items()
        for item in plan_items:
            if not self.stage_plan(item):
                break  # Stop staging if an error occurs


class BasicPlanWidget(PlanWidgetBase):
    """
    Basic plan widget with optional dropdown menu for plan selection.

    Parameters
    ----------
    model : object
        The model object containing run_engine and user_status
    parent : QWidget, optional
        Parent widget
    plans : str or dict
        If str, used as item name for submission
        If dict, used to create drop-down menu
    **kwargs : dict
        Additional keyword arguments
    """

    def __init__(self, model, parent=None, plans="", params=None, **kwargs):
        super().__init__(model, parent)
        self.params = params if params is not None else []
        self.plans = plans
        if isinstance(plans, str):
            self.current_plan = plans

        self.basePlanLayout = QVBoxLayout()
        self.layout.addLayout(self.basePlanLayout)
        self.editingFinished.connect(self.check_plan_ready)
        self.setup_widget()

    def current_plan_changed(self, idx=None):
        plan_display = self.plan_combo_list.currentText()
        if plan_display in self.plans:
            self.current_plan = self.plans[plan_display]
        else:
            self.current_plan = None

    def setup_widget(self):
        if isinstance(self.plans, dict):
            self.plan_combo_list = QComboBox()
            for display_key in self.plans.keys():
                self.plan_combo_list.addItem(display_key)
            self.plan_combo_list.currentIndexChanged.connect(self.current_plan_changed)
            h = QHBoxLayout()
            h.addWidget(QLabel("Plan Subtype"))
            h.addWidget(self.plan_combo_list)
            self.basePlanLayout.addLayout(h)
            self.current_plan_changed()

    def _check_ready(self):
        return all(widget.check_ready() for widget in self.params)

    def reset(self):
        """
        Reset all parameter widgets.
        """
        for widget in self.params:
            widget.reset()

    def get_params(self):
        """
        Get parameters from the input widgets.

        Returns
        -------
        dict
            A dictionary of parameters
        """
        params = {}
        for widget in self.params:
            params.update(widget.get_params())
        return params

    def create_plan_items(self):
        """
        Create and return a list of plan items to be submitted.
        This method should be implemented by child classes.

        Returns
        -------
        list
            A list of BPlan items to be submitted.
        """
        raise NotImplementedError("This method should be implemented by child classes.")


class AutoPlanWidget(BasicPlanWidget):
    def __init__(self, model, parent=None, plans="", **kwargs):
        """
        If plan is a string, it will be used as the item name for submission
        If it is a dict, it will be used to create a drop-down menu
        """
        self.initial_kwargs = kwargs
        super().__init__(model, parent, plans)

    def setup_widget(self):
        # print("BasicPlanWidget setup_widget")
        super().setup_widget()
        self.planWidget = AutoParamGroup(self.model, self, **self.initial_kwargs)
        self.planWidget.editingFinished.connect(self.editingFinished)
        # print("Updating input widgets")
        self.params.append(self.planWidget)
        # print("Adding widget to layout")
        self.layout.addWidget(self.planWidget)
        # print("BasicPlanWidget setup_widget finished")


class MultiPlanWidget(PlanWidgetBase):
    """
    A widget that contains multiple plan widgets with checkboxes for selection.

    Parameters
    ----------
    model : object
        The model object containing run_engine and user_status
    parent : QWidget, optional
        Parent widget
    plan_widgets : list
        List of PlanWidgetBase instances to include
    """

    def __init__(self, model, parent=None, plan_widgets=None):
        super().__init__(model, parent)
        self.plan_widgets = plan_widgets or []
        self.widget_checkboxes = {}

        # Create button layout
        self.button_layout = QHBoxLayout()
        self.check_all_button = QPushButton("Check All")
        self.uncheck_all_button = QPushButton("Uncheck All")

        # Connect button signals
        self.check_all_button.clicked.connect(self.check_all)
        self.uncheck_all_button.clicked.connect(self.uncheck_all)

        # Add buttons to layout
        self.button_layout.addWidget(self.check_all_button)
        self.button_layout.addWidget(self.uncheck_all_button)
        self.button_layout.addStretch()

        # Add button layout to main layout
        self.layout.addLayout(self.button_layout)

        self.setup_widget()

    def setup_widget(self):
        """Set up the widget layout with checkboxes and plan widgets"""
        # Clear existing widgets (except buttons) if needed
        while self.layout.count() > 1:  # Keep button layout
            item = self.layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        for plan_widget in self.plan_widgets:
            # Create container widget and layout
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Create checkbox with label
            checkbox = QCheckBox(getattr(plan_widget, "display_name", "Unnamed Plan"))
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.check_plan_ready)
            container_layout.addWidget(checkbox)

            # Add plan widget with stretch
            container_layout.addWidget(plan_widget, stretch=1)

            # Store checkbox reference
            self.widget_checkboxes[plan_widget] = checkbox

            # Connect plan widget signals
            plan_widget.plan_ready.connect(self.check_plan_ready)

            # Add to main layout
            self.layout.addWidget(container)

        # Add vertical stretch at the end
        self.layout.addStretch()

        # Initial color update
        self.update_all_checkbox_colors()

    def check_all(self):
        """Check all checkboxes"""
        for checkbox in self.widget_checkboxes.values():
            checkbox.setChecked(True)
        self.check_plan_ready()

    def uncheck_all(self):
        """Uncheck all checkboxes"""
        for checkbox in self.widget_checkboxes.values():
            checkbox.setChecked(False)
        self.check_plan_ready()

    def add_plan_widget(self, widget):
        """
        Add a new plan widget to the list.

        Parameters
        ----------
        widget : PlanWidgetBase
            Plan widget to add
        """
        self.plan_widgets.append(widget)
        self.setup_widget()

    def update_checkbox_color(self, widget, ready):
        """
        Update the color of a checkbox label based on the widget's ready state.

        Parameters
        ----------
        widget : PlanWidgetBase
            The widget whose checkbox color needs to be updated
        ready : bool
            Whether the widget is ready
        """
        checkbox = self.widget_checkboxes.get(widget)
        if checkbox and checkbox.isChecked():
            palette = checkbox.palette()
            color = QColor(Qt.black) if ready else QColor(Qt.red)
            palette.setColor(QPalette.WindowText, color)
            checkbox.setPalette(palette)

    def update_all_checkbox_colors(self):
        """Update colors for all checkboxes based on their widgets' ready states"""
        for widget, checkbox in self.widget_checkboxes.items():
            try:
                ready = widget._check_ready()
                self.update_checkbox_color(widget, ready)
            except Exception:
                self.update_checkbox_color(widget, False)

    def check_plan_ready(self):
        """
        Check if any selected plan is ready and emit plan_ready signal.
        """

        # Use _check_ready to get the state without emitting signals
        ready_state = self._check_ready()

        # Update checkbox colors
        self.update_all_checkbox_colors()
        self.plan_ready.emit(ready_state)

    def _check_ready(self):
        """
        Check if any selected plan is ready.

        Returns
        -------
        bool
            True if any selected plan is ready, False otherwise
        """
        # print("[MultiPlanWidget] Getting selected widgets")
        selected_widgets = [
            widget
            for widget, checkbox in self.widget_checkboxes.items()
            if checkbox.isChecked()
        ]
        # print(f"[MultiPlanWidget] Found {len(selected_widgets)} selected widgets")

        if not selected_widgets:
            # print("[MultiPlanWidget] No widgets selected, returning False")
            return False

        ready_states = []
        for widget in selected_widgets:
            try:
                # print(
                #    f"[MultiPlanWidget] Checking ready state for {widget.display_name}"
                # )
                ready = widget._check_ready()  # Use the direct check method
                # print(
                #    f"[MultiPlanWidget] Widget {widget.display_name} ready state: {ready}"
                # )
                ready_states.append(ready)
            except Exception as e:
                # print(
                #    f"[MultiPlanWidget] Error checking widget {widget.display_name}: {str(e)}"
                # )
                ready_states.append(False)

        final_state = all(ready_states)
        return final_state

    def create_plan_items(self):
        """
        Create and return a list of plan items from selected widgets.

        Returns
        -------
        list
            Combined list of BPlan items from all selected plan widgets
        """
        all_items = []
        for widget, checkbox in self.widget_checkboxes.items():
            if checkbox.isChecked():
                try:
                    items = widget.create_plan_items()
                    all_items.extend(items)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Plan Creation Warning",
                        f"Failed to create plans from widget: {str(e)}",
                    )
        return all_items

    def reset(self):
        """Reset all plan widgets"""
        for widget in self.plan_widgets:
            widget.reset()
