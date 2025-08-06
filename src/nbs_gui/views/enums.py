from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QLabel,
    QHBoxLayout,
    QComboBox,
    QFrame,
)
from qtpy.QtCore import Qt


class EnumControl(QWidget):
    """Widget for controlling enum values with fixed-width styling."""

    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        """
        Initialize the enum widget.

        Parameters
        ----------
        model : object
            The model to monitor/control.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        orientation : str, optional
            The orientation of the widget ('h' or 'v').
        """
        super().__init__(**kwargs)
        print(f"Initializing EnumControl for model: {model.label}")
        self.model = model

        if orientation == "v":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        box.setContentsMargins(2, 1, 2, 1)
        box.setSpacing(2)

        # Label with expanding space after it
        self.label = QLabel(model.label)
        self.label.setFixedHeight(20)
        box.addWidget(self.label)
        box.addStretch()

        # Right-aligned value display with sunken frame
        self.value = QLabel("")
        self.value.setFrameStyle(QFrame.Box)
        self.value.setFixedWidth(100)
        self.value.setFixedHeight(20)
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Fixed-width combo box
        self.combo = QComboBox()
        self.combo.setFixedWidth(100)
        self.combo.setFixedHeight(20)

        box.addWidget(self.value)
        box.addWidget(self.combo)

        if orientation == "h":
            box.setAlignment(Qt.AlignVCenter)

        self.setLayout(box)

        # Initialize the combo box
        self.updateCombo(model.enum_strs)
        self.model.valueChanged.connect(self.setText)
        self.model.enumChanged.connect(self.updateCombo)
        self.combo.currentTextChanged.connect(self.setValue)

    def setText(self, val):
        """Update the displayed value and combo box selection.

        Parameters
        ----------
        val : str
            Current value to display
        """
        if val is None:
            val = "Disconnected"
            self.value.setText(val)
            self.combo.setCurrentIndex(-1)
            return
        else:
            self.value.setText(val)
            index = self.combo.findText(val)
            if index >= 0:
                self.combo.setCurrentIndex(index)

    def updateCombo(self, enum_strs):
        """Update the combo box items.

        Parameters
        ----------
        enum_strs : tuple
            Tuple of strings to populate the combo box
        """
        self.combo.clear()
        self.combo.addItems(enum_strs)

    def setValue(self, value):
        """Set the model value.

        Parameters
        ----------
        value : str
            Value to set in the model
        """
        self.model.set(value)


class EnumMonitor(QWidget):
    """Widget for monitoring enum values with fixed-width styling."""

    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        """
        Initialize the enum widget.

        Parameters
        ----------
        model : object
            The model to monitor/control.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        orientation : str, optional
            The orientation of the widget ('h' or 'v').
        """
        super().__init__(**kwargs)
        print(f"Initializing EnumMonitor for model: {model.label}")
        self.model = model

        if orientation == "v":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        box.setContentsMargins(2, 1, 2, 1)
        box.setSpacing(2)

        # Label with expanding space after it
        self.label = QLabel(model.label)
        self.label.setFixedHeight(20)
        box.addWidget(self.label)
        box.addStretch()

        # Right-aligned value display with sunken frame
        self.value = QLabel("")
        self.value.setFrameStyle(QFrame.Box)
        self.value.setFixedWidth(100)
        self.value.setFixedHeight(20)
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        box.addWidget(self.value)

        if orientation == "h":
            box.setAlignment(Qt.AlignVCenter)

        self.model.valueChanged.connect(self.setText)
        self.setLayout(box)

        # Initialize the value
        self.setText(self.model._value)

    def setText(self, val):
        """Update the displayed value.

        Parameters
        ----------
        val : str
            Value to display
        """
        if val is None:
            val = "Disconnected"
        self.value.setText(str(val))
