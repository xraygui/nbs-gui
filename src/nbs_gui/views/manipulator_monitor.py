from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QWidget
from .motor import MotorMonitor, MotorControl


class RealManipulatorControl(QGroupBox):
    """
    Displays a group of real axis controls for a manipulator.

    Parameters
    ----------
    manipulator : object
        The manipulator model to display the real axis controls for.
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str, optional
        The orientation of the widget ('h' or 'v').
    *args
        Variable length argument list.
    **kwargs
        Arbitrary keyword arguments.
    """

    def __init__(self, manipulator, parent_model=None, orientation=None, **kwargs):
        super().__init__(manipulator.label + " Real Axes", **kwargs)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)  # Adjust spacing as needed
        self.layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        for m in manipulator.real_axes_models:
            widget = MotorControl(m, parent_model)
            self.layout.addWidget(widget)


class PseudoManipulatorControl(QGroupBox):
    def __init__(self, manipulator, parent_model=None, orientation=None, **kwargs):
        super().__init__(manipulator.label + " Pseudoaxes", **kwargs)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)  # Adjust spacing as needed
        self.layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        for m in manipulator.pseudo_axes_models:
            widget = MotorControl(m, parent_model)
            self.layout.addWidget(widget)


class RealManipulatorMonitor(QGroupBox):
    def __init__(self, manipulator, parent_model=None, orientation=None, **kwargs):
        super().__init__(manipulator.label + " Real Axes", **kwargs)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)  # Adjust spacing as needed
        self.layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        for m in manipulator.real_axes_models:
            widget = MotorMonitor(m, parent_model)
            self.layout.addWidget(widget)


class PseudoManipulatorMonitor(QGroupBox):
    def __init__(self, manipulator, parent_model=None, orientation=None, **kwargs):
        super().__init__(manipulator.label + " Pseudoaxes", **kwargs)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(5)  # Adjust spacing as needed
        self.layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        for m in manipulator.pseudo_axes_models:
            widget = MotorMonitor(m, parent_model)
            self.layout.addWidget(widget)


class ManipulatorMonitor(QWidget):
    def __init__(
        self, manipulator, parent_model=None, orientation=None, parent=None, **kwargs
    ):
        super().__init__(parent=parent)
        hbox = QHBoxLayout()
        hbox.addWidget(
            RealManipulatorMonitor(manipulator, parent_model, orientation, **kwargs)
        )
        hbox.addWidget(
            PseudoManipulatorMonitor(manipulator, parent_model, orientation, **kwargs)
        )
        self.setLayout(hbox)


class ManipulatorControl(QWidget):
    def __init__(
        self, manipulator, parent_model=None, orientation=None, parent=None, **kwargs
    ):
        super().__init__(parent=parent)
        hbox = QHBoxLayout()
        hbox.addWidget(
            RealManipulatorControl(manipulator, parent_model, orientation, **kwargs)
        )
        hbox.addWidget(
            PseudoManipulatorControl(manipulator, parent_model, orientation, **kwargs)
        )
        self.setLayout(hbox)
