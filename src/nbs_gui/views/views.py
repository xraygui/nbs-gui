from qtpy.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QMenu,
    QAction,
    QWidget,
    QLabel,
    QStackedWidget,
    QSizePolicy,
)
from ..widgets.qt_custom import ScrollingComboBox


def AutoMonitor(model, parent_model=None, orientation="h"):
    """
    Takes a model, and automatically creates and returns a widget to monitor the model.

    Parameters
    ----------
    model : object
        Any model class that wraps a device.
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str
        Layout orientation ('h' or 'v').
    """
    print(f"Initializing AutoMonitor for model: {model.label}")
    Monitor = model.default_monitor
    try:
        return Monitor(model, parent_model=parent_model, orientation=orientation)
    except Exception as e:
        print(f"Exception {e} in AutoMonitor for {model.name}")
        raise e


def AutoControl(model, parent_model=None, orientation="h"):
    """Create an appropriate widget to control the model.

    Parameters
    ----------
    model : BaseModel
        Model containing device information and state
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str
        Layout orientation ('h' or 'v')

    Returns
    -------
    QWidget
        Either a DynamicControlWidget or a simple monitor/controller
    """
    print(f"Initializing AutoControl for model: {model.label}")
    try:
        if hasattr(model, "availability_changed"):
            print("Adding DynamicControlWidget for model: ", model.label)
            widget = DynamicControlWidget(
                model, parent_model=parent_model, orientation=orientation
            )
        elif getattr(model, "view_only", False):
            print(
                "Adding default monitor {} for model: {}".format(
                    model.default_monitor, model.label
                )
            )
            widget = model.default_monitor(
                model, parent_model=parent_model, orientation=orientation
            )
        else:
            print(
                "Adding default controller {} for model: {}".format(
                    model.default_controller, model.label
                )
            )
            widget = model.default_controller(
                model, parent_model=parent_model, orientation=orientation
            )
        return widget
    except Exception as e:
        print(f"Exception {e} in AutoControl for {model.name}")
        raise e


class AutoControlBox(QGroupBox):
    """
    A widget that automatically generates control interfaces for a given set of models.

    Parameters
    ----------
    models : dict, list
        A container with model objects for which control interfaces are to be generated.
    title : str
        The title of the group box.
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str, optional
        The orientation of the control interface box. Can be 'h' for horizontal or 'v' for vertical. Default is 'h'.
    """

    def __init__(self, models, title, parent_model=None, orientation="h"):
        super().__init__(title)
        print(f"Initializing AutoControlBox {title}")
        self.widgets = {}
        if orientation == "h":
            self.box = QHBoxLayout()
            widget_orientation = "v"
        else:
            self.box = QVBoxLayout()
            widget_orientation = "h"
        self.box.setContentsMargins(5, 5, 5, 5)
        self.box.setSpacing(5)

        # Filter models that have controllers
        controllable_models = {}

        if isinstance(models, dict):
            for k, m in models.items():
                # Check if model has a controller
                if (
                    hasattr(m, "default_controller")
                    and m.default_controller is not None
                ):
                    controllable_models[k] = m
                else:
                    print(f"Skipping {k} - no controller available")
        elif isinstance(models, list):
            for m in models:
                # Check if model has a controller
                if (
                    hasattr(m, "default_controller")
                    and m.default_controller is not None
                ):
                    controllable_models[m.label] = m
                else:
                    print(f"Skipping {m.label} - no controller available")

        # Create widgets only for controllable models
        for k, m in controllable_models.items():
            try:
                widget = AutoControl(
                    m, parent_model=parent_model, orientation=widget_orientation
                )
                self.widgets[k] = widget
                self.box.addWidget(widget)
                widget.setVisible(getattr(m, "visible", True))
            except Exception as e:
                print(f"Failed to create control widget for {k}: {e}")

        # If no controllable models, add a message
        if not controllable_models:
            no_controls_label = QLabel("No controllable devices found")
            no_controls_label.setAlignment(Qt.AlignCenter)
            self.box.addWidget(no_controls_label)

        self.setLayout(self.box)

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)

        for widget_name, widget in self.widgets.items():
            action = QAction(widget_name, self)
            action.setCheckable(True)
            action.setChecked(widget.isVisible())
            action.triggered.connect(lambda checked, w=widget: w.setVisible(checked))
            contextMenu.addAction(action)

        # show the context menu at the event's position
        contextMenu.exec_(event.globalPos())


class AutoMonitorBox(QGroupBox):
    """
    A widget that automatically generates a monitor interface for a given set of models.

    Parameters
    ----------
    models : dict, list
        A container with model objects to be monitored.
    title : str
        The title of the group box.
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str, optional
        The orientation of the monitor box. Can be 'h' for horizontal or 'v' for vertical. Default is 'h'.
    """

    def __init__(self, models, title, parent_model=None, orientation="h"):
        super().__init__(title)
        print(f"Initializing AutoMonitorBox {title}")
        self.widgets = {}
        if orientation == "h":
            self.box = QHBoxLayout()
            widget_orientation = "v"
        else:
            self.box = QVBoxLayout()
            widget_orientation = "h"
        self.box.setContentsMargins(5, 5, 5, 5)
        self.box.setSpacing(5)
        if isinstance(models, dict):
            print(f"Adding {models.keys()} to AutoMonitorBox")
            for k, m in models.items():
                if m is None:
                    print(f"Skipping {k} - no model available")
                    continue
                print(f"Adding {m.label} to AutoMonitorBox")
                widget = AutoMonitor(
                    m, parent_model=parent_model, orientation=widget_orientation
                )

                self.widgets[k] = widget
                self.box.addWidget(widget)
                widget.setVisible(getattr(m, "visible", True))
        elif isinstance(models, list):
            print(f"Adding {models} to AutoMonitorBox")
            for m in models:
                if m is None:
                    print(f"Skipping None - no model available")
                    continue
                print(f"Adding {m.label} to AutoMonitorBox")
                widget = AutoMonitor(
                    m, parent_model=parent_model, orientation=widget_orientation
                )

                self.widgets[m.label] = widget
                self.box.addWidget(widget)
                widget.setVisible(getattr(m, "visible", True))
        self.setLayout(self.box)

    def contextMenuEvent(self, event):
        contextMenu = QMenu(self)

        for widget_name, widget in self.widgets.items():
            action = QAction(widget_name, self)
            action.setCheckable(True)
            action.setChecked(widget.isVisible())
            action.triggered.connect(lambda checked, w=widget: w.setVisible(checked))
            contextMenu.addAction(action)

        # show the context menu at the event's position
        contextMenu.exec_(event.globalPos())


class AutoControlCombo(QWidget):
    def __init__(
        self, modelDict, title, parent_model=None, *args, orientation="h", **kwargs
    ):
        """
        Initializes an AutoControlCombo widget with a dropdown to select between different models.

        Parameters
        ----------
        modelDict : dict
            A dictionary mapping model names to model instances. These models are used to populate
            the dropdown and the stacked widget.
        title : str
            The title label for the combo box.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        *args
            Variable length argument list for QWidget.
        orientation : str, optional
            The orientation for the AutoControl widgets. Can be 'h' for horizontal or 'v' for
            vertical. Defaults to 'h'.
        **kwargs
            Arbitrary keyword arguments for QWidget.
        """
        super().__init__(*args, **kwargs)
        print(f"Initializing AutoControlCombo {title}")
        controlBox = QVBoxLayout()
        selectBox = QHBoxLayout()
        label = QLabel(title)
        dropdown = ScrollingComboBox(max_visible_items=10)

        widgetStack = QStackedWidget()
        keys = sorted(modelDict.keys())

        for key in keys:
            print(f"Adding {key} to AutoControlCombo")
            model = modelDict.get(key, None)
            if model:
                if model.default_controller is None:
                    continue
                dropdown.addItem(key)
                print(f"Adding model {model.label} to widgetStack")
                widgetStack.addWidget(
                    AutoControl(
                        model, parent_model=parent_model, orientation=orientation
                    )
                )
            else:
                print(f"Model with key {key} is not loaded!")
        dropdown.currentIndexChanged.connect(widgetStack.setCurrentIndex)
        selectBox.addWidget(label)
        selectBox.addWidget(dropdown)
        controlBox.addLayout(selectBox)
        controlBox.addWidget(widgetStack)
        self.setLayout(controlBox)

        # Set size policy for widgetStack
        widgetStack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        print(f"AutoControlCombo {title} initialized")


class DynamicControlWidget(QStackedWidget):
    """Widget that switches between monitor and control views based on availability.

    Parameters
    ----------
    model : BaseModel
        Model containing device information and state
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    orientation : str
        Layout orientation ('h' or 'v')
    """

    def __init__(self, model, parent_model=None, orientation="h"):
        super().__init__()
        self.model = model

        # Create both views
        self.monitor = model.default_monitor(
            model, parent_model=parent_model, orientation=orientation
        )
        if not getattr(model, "view_only", False):
            self.controller = model.default_controller(
                model, parent_model=parent_model, orientation=orientation
            )
        else:
            self.controller = None

        # Add views to stack
        self.addWidget(self.monitor)
        if self.controller:
            self.addWidget(self.controller)

        # Connect to availability changes if model supports it
        if hasattr(model, "availability_changed"):
            model.availability_changed.connect(self._handle_availability)
            # Set initial state
            self._handle_availability(model.is_available)
        elif self.controller:
            # No mode management, default to controller if available
            self.setCurrentWidget(self.controller)

    def _handle_availability(self, available):
        """Switch between monitor and controller based on availability."""
        if available and self.controller:
            self.setCurrentWidget(self.controller)
        else:
            self.setCurrentWidget(self.monitor)
