from qtpy.QtWidgets import QVBoxLayout, QGroupBox, QWidget, QHBoxLayout
from .views import AutoControl, AutoMonitor


class MotorTupleBox(QWidget):
    """
    Base class for a simple motor tuple view.

    This is a simple widget that displays motors in a single group box,
    without the complexity of switchable views.
    """

    def __init__(
        self, model, parent_model=None, title=None, orientation=None, **kwargs
    ):
        """
        Initialize the motor tuple widget.

        Parameters
        ----------
        model : object
            The model to monitor/control.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        title : str, optional
            The title of the widget.
        orientation : str, optional
            The orientation of the widget ('h' or 'v').
        """
        super().__init__(**kwargs)
        self.model = model
        self.parent_model = parent_model
        base_title = title if title is not None else model.label

        # Create main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Create single group box for motors
        self.motors_box = QGroupBox(base_title)
        self.motors_layout = QVBoxLayout()
        self.motors_box.setLayout(self.motors_layout)

        # Add box to layout
        self.layout.addWidget(self.motors_box)


class MotorTupleMonitor(MotorTupleBox):
    """
    Monitor widget for a tuple of motors.
    Shows all motors in a simple, compact layout.

    Parameters
    ----------
    model : MotorTupleModel
        The model representing the motor tuple
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    title : str, optional
        Title for the group box
    """

    def __init__(self, model, parent_model=None, title=None, **kwargs):
        super().__init__(model, parent_model=parent_model, title=title, **kwargs)

        # Add motor monitors
        for motor in model.real_motors:
            self.motors_layout.addWidget(AutoMonitor(motor, parent_model))


class MotorTupleControl(MotorTupleBox):
    """
    Control widget for a tuple of motors.
    Shows all motors in a simple, compact layout.

    Parameters
    ----------
    model : MotorTupleModel
        The model representing the motor tuple
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    title : str, optional
        Title for the group box
    """

    def __init__(self, model, parent_model=None, title=None, **kwargs):
        super().__init__(model, parent_model=parent_model, title=title, **kwargs)

        # Add motor controls
        for motor in model.real_motors:
            self.motors_layout.addWidget(AutoControl(motor, parent_model))
