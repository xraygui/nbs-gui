from qtpy.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QVBoxLayout,
    QGroupBox,
    QFrame,
    QScrollArea,
    QProgressBar,
    QMessageBox,
)
from qtpy.QtCore import Slot, Qt
from qtpy.QtGui import QColor
import numpy as np

from ..widgets.utils import SquareByteIndicator


class MotorMonitor(QWidget):
    def __init__(self, model, parent_model=None, orientation="h", *args, **kwargs):
        """
        Initialize the motor widget.

        Parameters
        ----------
        model : object
            The model to monitor/control.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        orientation : str, optional
            The orientation of the widget ('h' or 'v').
        """
        super().__init__(*args, **kwargs)
        # print(f"[{model.label}] Initializing MotorMonitor")
        self.model = model
        if orientation == "h":
            self.box = QHBoxLayout()
        else:
            self.box = QVBoxLayout()
        if model.units is not None:
            self.units = model.units
        else:
            self.units = ""
        self.box.setSpacing(2)
        self.box.setContentsMargins(2, 1, 2, 1)

        # Label with expanding space after it
        self.label = QLabel(self.model.label)
        self.label.setFixedHeight(20)
        self.box.addWidget(self.label)
        self.box.addStretch()

        # Right-aligned position display with sunken frame
        self.position = QLabel(self.model.value)
        self.position.setFrameStyle(QFrame.Box)
        self.position.setFixedWidth(100)
        self.position.setFixedHeight(20)
        self.position.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # print(f"[{self.model.label}] Position: {self.model.value}")
        self.box.addWidget(self.position)

        # Status indicator
        self.indicator = SquareByteIndicator()
        self.indicator.setFixedSize(18, 18)
        self.box.addWidget(self.indicator)

        if orientation == "h":
            self.box.setAlignment(Qt.AlignVCenter)
        self.model.valueChanged.connect(self.update_position)
        self.model.movingStatusChanged.connect(self.update_indicator)
        self.setLayout(self.box)

    @Slot(str)
    def update_position(self, value):
        if value is None:
            value = "Disconnected"
        # print(f"[MotorMonitor {self.model.label}] update_position: {value}")
        self.position.setText(f"{value} {self.units}")

    @Slot(bool)
    def update_indicator(self, status):
        color = "green" if status else "grey"
        self.indicator.setColor(color)


class MotorControl(MotorMonitor):
    def __init__(self, model, *args, **kwargs):
        # print(f"[{model.label}] Initializing MotorControl")
        super().__init__(model, *args, **kwargs)
        # Fixed-width input field
        self.lineEdit = QLineEdit()
        self.lineEdit.setFixedWidth(100)
        self.lineEdit.setFixedHeight(20)
        self.lineEdit.setAlignment(Qt.AlignRight)
        initial_sp = self.model.setpoint
        if initial_sp is not None:
            # print(f"[{self.model.label}] Initial setpoint: {initial_sp}")
            self.lineEdit.setText("{:2f}".format(initial_sp))
        else:
            self.lineEdit.setText("Disconnected")
            self.lineEdit.setEnabled(False)

        self.lineEdit.returnPressed.connect(self.enter_position)
        self.model.setpointChanged.connect(self.update_sp)

        # Insert widgets in order: label, stretch, position, input, move, tweak, stop
        self.box.insertWidget(3, self.lineEdit)  # After position display

        # Control buttons with consistent sizes
        self.gobutton = QPushButton("Move")
        self.gobutton.setFixedWidth(60)
        self.gobutton.setFixedHeight(20)
        self.gobutton.clicked.connect(self.enter_position)

        self.lbutton = QPushButton("<")
        self.lbutton.setFixedWidth(30)
        self.lbutton.setFixedHeight(20)
        self.lbutton.clicked.connect(self.tweak_left)

        self.tweakEdit = QLineEdit()
        self.tweakEdit.setFixedWidth(50)
        self.tweakEdit.setFixedHeight(20)
        self.tweakEdit.setAlignment(Qt.AlignRight)
        self.tweakEdit.setText("1")

        self.rbutton = QPushButton(">")
        self.rbutton.setFixedWidth(30)
        self.rbutton.setFixedHeight(20)
        self.rbutton.clicked.connect(self.tweak_right)

        self.stopButton = QPushButton("Stop!")
        self.stopButton.setFixedWidth(60)
        self.stopButton.setFixedHeight(20)
        self.stopButton.clicked.connect(lambda x: self.model.stop())

        # Add remaining widgets in sequence
        self.box.addWidget(self.gobutton)
        self.box.addWidget(self.lbutton)
        self.box.addWidget(self.tweakEdit)
        self.box.addWidget(self.rbutton)
        self.box.addWidget(self.stopButton)

        # Update initial state
        self.update_widget_states(self.model.connected)
        self.model.connectionStatusChanged.connect(self.update_widget_states)

    def update_widget_states(self, is_connected):
        """Update widget states based on connection status."""

        print(
            f"[{self.model.label}.update_widget_states] Updating widget states, is_connected: {is_connected}"
        )

        self.lineEdit.setEnabled(is_connected)
        self.gobutton.setEnabled(is_connected)
        self.lbutton.setEnabled(is_connected)
        self.rbutton.setEnabled(is_connected)
        self.tweakEdit.setEnabled(is_connected)
        self.stopButton.setEnabled(is_connected)

        if not is_connected:
            self.position.setText("Disconnected")
            self.lineEdit.setText("Disconnected")
            self.indicator.setColor("red")
        else:
            self.update_position(self.model.value)
            self.update_sp(self.model.setpoint)
            self.update_indicator(self.model.moving)

    def check_limits(self, value):
        """
        Check if value is within motor limits.

        Parameters
        ----------
        value : float
            Value to check

        Returns
        -------
        bool
            True if within limits, False otherwise
        """

        if hasattr(self.model, "limits"):
            low, high = self.model.limits

            if low == high:
                # If the limits are the same, they are probably not really set
                return True
            if low is not None and value < low:
                self.show_limit_error(value, f"below lower limit of {low}")
                return False
            if high is not None and value > high:
                self.show_limit_error(value, f"above upper limit of {high}")
                return False
        return True

    def show_limit_error(self, value, limit_desc):
        """Show error message for limit violation."""
        QMessageBox.warning(
            self,
            "Limit Error",
            f"Cannot move {self.model.label} to {value}:\n" f"Value is {limit_desc}",
        )

    def enter_position(self):
        """Handle direct position entry."""
        try:
            newpos = float(self.lineEdit.text())
            print(f"[{self.model.label}] Direct entry: setting to {newpos}")
            if self.check_limits(newpos):
                self.model.set(newpos)
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                f"Invalid input for {self.model.label}:\n"
                f"Please enter a valid number",
            )

    def tweak_left(self):
        """Decrement position by step size."""
        try:
            current_sp = self.model.setpoint
            step = float(self.tweakEdit.text())
            new_sp = current_sp - step
            print(f"[{self.model.label}] Tweak left: {current_sp} - {step} = {new_sp}")
            if self.check_limits(new_sp):
                self.model.set(new_sp)
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                f"Invalid step size for {self.model.label}:\n"
                f"Please enter a valid number in the step size field",
            )

    def tweak_right(self):
        """Increment position by step size."""
        try:
            current_sp = self.model.setpoint
            step = float(self.tweakEdit.text())
            new_sp = current_sp + step
            print(f"[{self.model.label}] Tweak right: {current_sp} + {step} = {new_sp}")
            if self.check_limits(new_sp):
                self.model.set(new_sp)
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                f"Invalid step size for {self.model.label}:\n"
                f"Please enter a valid number in the step size field",
            )

    def update_sp(self, value):
        """Update displayed setpoint when it changes."""
        # Don't update if user is editing
        if self.lineEdit.hasFocus():
            print(f"{self.model.label} has focus")
            return
        else:
            print(f"{self.model.label} sp update to {value}")

        if value is None:
            self.lineEdit.setText("Disconnected")
            self.lineEdit.setEnabled(False)
            return

        self.lineEdit.setEnabled(True)
        if isinstance(value, (int, float)):
            self.lineEdit.setText("{:2f}".format(value))
        elif isinstance(value, str):
            self.lineEdit.setText(value)
        else:
            self.lineEdit.setText(str(value))


class MotorProgressBar(QWidget):
    def __init__(self, model, parent_model, parent=None):
        super().__init__(parent=parent)
        self.model = model

        print(f"[{self.model.label}] Initializing MotorProgressBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.label = QLabel(self.model.label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)  # Set range to 0-100 for percentage

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar, 1)

        self.start_value = 0
        self.end_value = 1  # To avoid division by zero

        # Initialize with current values
        self.update_range(self.model.setpoint)
        self.update_progress(self.model.position)

        # Connect signals
        print(f"[{self.model.label}] Connecting signals")
        self.model.valueChanged.connect(self.update_progress)
        self.model.setpointChanged.connect(self.update_range)
        self.model.movingStatusChanged.connect(self.on_moving_status_changed)
        print(f"[{self.model.label}] MotorProgressBar initialized")

    def update_range(self, setpoint):
        """Update the progress bar range with new setpoint."""
        # print(f"[{self.model.label}.update_range] Updating range")

        if setpoint is None or self.model.position is None:
            # print(f"[{self.model.label}.update_range] Progress bar disabled")
            self.progress_bar.setEnabled(False)
            self.label.setText(f"{self.model.label}: DISCONNECTED")
            return

        # print(f"[{self.model.label}.update_range] Progress bar enabled")
        self.progress_bar.setEnabled(True)
        current_value = float(self.model.position)
        setpoint = float(setpoint)
        self.start_value = current_value
        self.end_value = setpoint
        self.update_progress(current_value)

    def update_progress(self, value):
        """Update progress bar with new value."""
        # print(
        #     f"[{self.model.label}.update_progress] Updating progress with value {value}"
        # )
        if value is None or self.model.setpoint is None or value == "None":
            self.progress_bar.setEnabled(False)
            self.label.setText(f"{self.model.label}: Disconnected")
            return
        # print(f"[{self.model.label}.update_progress] Progress bar enabled")
        self.progress_bar.setEnabled(True)
        try:
            value = float(value)
        except ValueError:
            print(f"[{self.model.label}.update_progress] Value {value} is not a number")
            return
        if self.end_value != self.start_value:
            # Calculate percentage completion
            percent_complete = (
                (value - self.start_value) / (self.end_value - self.start_value) * 100
            )
            percent_complete = max(0, min(100, percent_complete))
            self.progress_bar.setValue(int(percent_complete))
        self.label.setText(f"{self.model.label}: {value:.3f} / {self.end_value:.3f}")

    def on_moving_status_changed(self, is_moving):
        """Handle changes in motor movement status."""
        if self.model.position is None or self.model.setpoint is None:
            self.progress_bar.setEnabled(False)
            return

        self.progress_bar.setEnabled(True)
        if is_moving:
            self.update_range(self.model.setpoint)
        else:
            self.progress_bar.reset()

    def sizeHint(self):
        return self.progress_bar.sizeHint()


class DynamicMotorBar(MotorProgressBar):
    def __init__(self, model, parent_model, **kwargs):
        super().__init__(model, parent_model, **kwargs)
        self.setVisible(False)  # Initially set to invisible
        self.model.movingStatusChanged.connect(self.update_visibility)
        # self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    @Slot(bool)
    def update_visibility(self, status):
        self.setVisible(status)


class DynamicMotorBox(QGroupBox):
    """
    A widget that automatically generates a monitor interface for a given set of models.
    """

    def __init__(self, models, title, parent_model, **kwargs):
        """
        Initializes the AutoMonitorBox widget with a set of models, a title, a parent model, and an orientation.

        Parameters
        ----------
        modelDict : dict
            A dictionary where keys are identifiers and values are model objects to be monitored.
        title : str
            The title of the group box.
        parent_model : object
            The parent model for the GUI.
        orientation : str, optional
            The orientation of the monitor box. Can be 'h' for horizontal or 'v' for vertical. Default is 'h'.
        """
        super().__init__(title)
        print(f"Initializing DynamicMotorBox with title: {title}")
        self.moving_motors = set()  # Track moving motors
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(1)

        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)

        self.motor_progress_widgets = []
        print("Models: ", models)
        if isinstance(models, dict):
            models = list(models.values())
        for m in models:
            if m is None:
                print("Model is None")
                continue
            print(f"Adding motor widget for model: {m.label}")
            if m.default_monitor == MotorMonitor:
                widget = DynamicMotorBar(m, parent_model)
                widget.setVisible(False)
                self.motor_progress_widgets.append(widget)
                self.content_layout.addWidget(widget)
                m.movingStatusChanged.connect(self.update_moving_status)
            if hasattr(m, "real_motors"):
                for motor in m.real_motors:
                    # print(f"Adding real axis motor widget for model: {motor.label}")
                    widget = DynamicMotorBar(motor, parent_model)
                    widget.setVisible(False)
                    self.motor_progress_widgets.append(widget)
                    self.content_layout.addWidget(widget)
                    motor.movingStatusChanged.connect(self.update_moving_status)

        self.content_layout.addStretch(1)

        # Add emergency stop button
        self.emergency_stop_button = QPushButton("Emergency Stop", self)
        self.emergency_stop_button.clicked.connect(self.emergency_stop)
        self.layout.addWidget(self.emergency_stop_button)

    @Slot(bool)
    def update_moving_status(self, is_moving):
        sender = self.sender()
        if is_moving:
            self.moving_motors.add(sender)
        else:
            self.moving_motors.discard(sender)

    def emergency_stop(self):
        for motor in self.moving_motors:
            motor.stop()


class BeamlineMotorBars(DynamicMotorBox):
    def __init__(self, model, **kwargs):
        beamline = model.beamline
        motors = (
            beamline.motors | beamline.manipulators | beamline.mirrors | beamline.source
        )
        super().__init__(motors, "Motor Progress Bars", model, **kwargs)
