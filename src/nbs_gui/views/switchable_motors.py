from qtpy.QtWidgets import QVBoxLayout, QGroupBox, QMenu, QAction, QWidget
from qtpy.QtCore import Qt
from .views import AutoControl, AutoMonitor


class SwitchableMotorBox(QWidget):
    """
    Base class for a switchable view between two sets of motors.

    Parameters
    ----------
    model : object
        Model containing the motors
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    pseudo_title : str, optional
        Title for pseudo motors box, defaults to "Pseudo Motors"
    real_title : str, optional
        Title for real motors box, defaults to "Real Motors"
    title : str, optional
        Base title for the boxes, defaults to model.label
    """

    def __init__(
        self,
        model,
        parent_model=None,
        pseudo_title="Pseudo Motors",
        real_title="Real Motors",
        title=None,
        orientation=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.parent_model = parent_model
        base_title = title if title is not None else model.label

        # Initialize showing_real_motors based on model's preference
        self.showing_real_motors = getattr(model, "show_real_motors_by_default", False)

        # Create main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Create pseudo motors box with combined title
        self.pseudo_box = QGroupBox(f"{base_title} - {pseudo_title}")
        self.pseudo_layout = QVBoxLayout()
        self.pseudo_box.setLayout(self.pseudo_layout)

        # Create real motors box with combined title
        self.real_box = QGroupBox(f"{base_title} - {real_title}")
        self.real_layout = QVBoxLayout()
        self.real_box.setLayout(self.real_layout)

        # Add boxes to layout
        self.layout.addWidget(self.pseudo_box)
        self.layout.addWidget(self.real_box)

        # Set initial visibility based on model's preference
        self.pseudo_box.setVisible(not self.showing_real_motors)
        self.real_box.setVisible(self.showing_real_motors)

        # Set up context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        """Show context menu for switching views."""
        menu = QMenu(self)

        # Create action for toggling between pseudo and real motors
        toggle_action = QAction(
            ("Show Pseudo Motors" if self.showing_real_motors else "Show Real Motors"),
            self,
        )
        toggle_action.triggered.connect(self.toggle_motors_view)
        menu.addAction(toggle_action)

        # Show menu at cursor position
        menu.exec_(self.mapToGlobal(pos))

    def toggle_motors_view(self):
        """Toggle between pseudo and real motors view."""
        self.showing_real_motors = not self.showing_real_motors
        self.pseudo_box.setVisible(not self.showing_real_motors)
        self.real_box.setVisible(self.showing_real_motors)


class SwitchableMotorMonitor(SwitchableMotorBox):
    """
    Monitor widget that can switch between pseudo and real motors.

    Parameters
    ----------
    model : object
        Model containing pseudo_motors and real_motors lists
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    pseudo_title : str, optional
        Title for pseudo motors box
    real_title : str, optional
        Title for real motors box
    title : str, optional
        Title for the group box
    """

    def __init__(self, model, parent_model=None, *args, **kwargs):
        super().__init__(model, parent_model=parent_model, *args, **kwargs)
        print(f"Setting up switchable motor monitor for model: {model.label}")
        # Add pseudo motor monitors
        for motor in model.pseudo_motors:
            self.pseudo_layout.addWidget(AutoMonitor(motor, parent_model))

        # Add real motor monitors
        for motor in model.real_motors:
            self.real_layout.addWidget(AutoMonitor(motor, parent_model))


class SwitchableMotorControl(SwitchableMotorBox):
    """
    Control widget that can switch between pseudo and real motors.

    Parameters
    ----------
    model : object
        Model containing pseudo_motors and real_motors lists
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    pseudo_title : str, optional
        Title for pseudo motors box
    real_title : str, optional
        Title for real motors box
    title : str, optional
        Title for the group box
    """

    def __init__(self, model, parent_model=None, *args, **kwargs):
        print(f"Setting up switchable motor control for model: {model.label}")
        super().__init__(model, parent_model=parent_model, *args, **kwargs)
        print("Adding pseudo motors")
        # Add pseudo motor controls
        for motor in model.pseudo_motors:
            self.pseudo_layout.addWidget(AutoControl(motor, parent_model))
        print("Adding real motors")
        # Add real motor controls
        for motor in model.real_motors:
            self.real_layout.addWidget(AutoControl(motor, parent_model))
