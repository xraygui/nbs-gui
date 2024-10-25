from qtpy.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QLineEdit,
    QVBoxLayout,
    QGroupBox,
    QSizePolicy,
    QScrollArea,
    QProgressBar,
)
from qtpy.QtCore import Slot, Qt, QTimer
from qtpy.QtCore import QSize

from .utils import SquareByteIndicator


class MotorMonitor(QWidget):
    def __init__(self, model, parent_model, orientation="h", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        if orientation == "h":
            self.box = QHBoxLayout()
        else:
            self.box = QVBoxLayout()
        if model.units is not None:
            self.units = model.units
        else:
            self.units = ""
        self.box.setSpacing(5)  # Adjust spacing as needed
        self.box.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.model.label)
        self.box.addWidget(self.label)
        self.position = QLabel(self.model.value)
        print(self.model.label, self.model.value)
        self.box.addWidget(self.position)
        self.indicator = SquareByteIndicator()
        self.box.addWidget(self.indicator)
        if orientation == "h":
            self.box.setAlignment(Qt.AlignVCenter)
        self.model.valueChanged.connect(self.update_position)
        self.model.movingStatusChanged.connect(self.update_indicator)
        self.setLayout(self.box)

    @Slot(str)
    def update_position(self, value):
        self.position.setText(f"{value} {self.units}")

    @Slot(bool)
    def update_indicator(self, status):
        color = "green" if status else "grey"
        self.indicator.setColor(color)


class MotorControl(MotorMonitor):
    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)
        self.lineEdit = QLineEdit()
        # self.lineEdit.returnPressed.connect(self.enter_position)

        self.lineEdit.setText("{:2f}".format(self.model.setpoint))
        self.lineEdit.returnPressed.connect(self.enter_position)
        self.model.setpointChanged.connect(self.update_sp)
        self.box.insertWidget(2, self.lineEdit)
        gobutton = QPushButton("Move")
        gobutton.clicked.connect(self.enter_position)
        lbutton = QPushButton("<")
        lbutton.clicked.connect(self.tweak_left)
        self.tweakEdit = QLineEdit()
        self.tweakEdit.setText("1")
        rbutton = QPushButton(">")
        rbutton.clicked.connect(self.tweak_right)
        stopButton = QPushButton("Stop!")
        stopButton.clicked.connect(self.model.stop)
        self.box.insertWidget(4, gobutton)
        self.box.insertWidget(5, lbutton)
        self.box.insertWidget(6, self.tweakEdit)
        self.box.insertWidget(7, rbutton)
        self.box.insertWidget(8, stopButton)

    def enter_position(self):
        newpos = float(self.lineEdit.text())
        self.model.set(newpos)

    def tweak_left(self):
        current_sp = self.model.setpoint
        step = float(self.tweakEdit.text())
        new_sp = current_sp - step
        self.model.set(new_sp)
        self.update_sp(new_sp)
        # self.lineEdit.setText(str(new_sp))

    def tweak_right(self):
        current_sp = self.model.setpoint
        step = float(self.tweakEdit.text())
        new_sp = current_sp + step
        self.model.set(new_sp)
        self.update_sp(new_sp)
        # self.lineEdit.setText(str(new_sp))

    def update_sp(self, value):
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.label = QLabel(self.model.label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)  # Hide default percentage text
        self.progress_bar.setRange(0, 1000)  # Set fixed range for progress bar

        layout.addWidget(self.label)
        layout.addWidget(
            self.progress_bar, 1
        )  # The '1' gives the progress bar more space

        # Initialize variables for normalization
        self.start_value = 0
        self.range = 1  # To avoid division by zero

        # Initialize progress bar
        self.update_range(self.model.setpoint)
        self.update_progress(self.model.value)

        # Connect to motor model signals
        self.model.valueChanged.connect(self.update_progress)
        self.model.setpointChanged.connect(self.update_range)
        self.model.movingStatusChanged.connect(self.on_moving_status_changed)

    def update_range(self, setpoint):
        current_value = float(self.model.value)
        setpoint = float(setpoint)
        self.start_value = min(current_value, setpoint)
        self.range = abs(setpoint - current_value)
        if self.range == 0:
            self.range = 1  # To avoid division by zero
        self.update_progress(current_value)

    def update_progress(self, value):
        value = float(value)

        normalized_value = (value - self.start_value) / self.range * 1000
        normalized_value = max(0, min(1000, normalized_value))  # Clamp to 0-100 range
        self.progress_bar.setValue(int(normalized_value))
        self.label.setText(f"{self.model.label}: {value:.3f}")

    def on_moving_status_changed(self, is_moving):
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
        print("Initializing DynamicMotorBox")
        self.moving_motors_count = 0
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
        if isinstance(models, dict):
            models = list(models.values())
        for m in models:
            if m.default_monitor == MotorMonitor:
                widget = DynamicMotorBar(m, parent_model)
                widget.setVisible(False)
                self.motor_progress_widgets.append(widget)
                self.content_layout.addWidget(widget)
                # m.movingStatusChanged.connect(self.update_visibility)
            if hasattr(m, "real_axes_models"):
                for motor in m.real_axes_models:
                    widget = DynamicMotorBar(motor, parent_model)
                    widget.setVisible(False)
                    self.motor_progress_widgets.append(widget)
                    self.content_layout.addWidget(widget)
                    # motor.movingStatusChanged.connect(self.update_visibility)

        self.content_layout.addStretch(1)
        print("Initializing DynamicMotorBox Widgets Done")

        # self.update_visibility(False)
        # print("Update Visibility Done")

        # # Use a timer to periodically check and update the size
        # self.update_timer = QTimer(self)
        # self.update_timer.timeout.connect(self.check_and_update_size)
        # self.update_timer.start(500)

    # def update_visibility(self, moving):
    #     if moving:
    #         self.moving_motors_count += 1
    #     else:
    #         self.moving_motors_count = max(0, self.moving_motors_count - 1)

    #     self.update_widget_visibility()

    # def update_widget_visibility(self):
    #     any_visible = self.moving_motors_count > 0
    #     # self.setVisible(any_visible)
    #     self.check_and_update_size()

    # def check_and_update_size(self):
    #     content_height = self.content_widget.sizeHint().height()
    #     self.scroll_area.setFixedHeight(
    #         min(content_height, 200)
    #     )  # Set a maximum height

    # def sizeHint(self):
    #     return self.scroll_area.sizeHint()

    # def minimumSizeHint(self):
    #     return QSize(200, 50)  # Adjust the width as needed


class BeamlineMotorBars(DynamicMotorBox):
    def __init__(self, model, **kwargs):
        beamline = model.beamline
        motors = (
            beamline.motors | beamline.manipulators | beamline.mirrors | beamline.source
        )
        super().__init__(motors, "Motor Progress Bars", model, **kwargs)
