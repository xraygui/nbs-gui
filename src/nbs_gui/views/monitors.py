from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFrame,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Qt


class PVControl(QWidget):
    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        """Initialize PV control widget with type-specific validation.

        Parameters
        ----------
        model : PVModel
            Model containing the PV to control
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        orientation : str, optional
            Layout orientation ('v' for vertical, 'h' for horizontal)
        **kwargs : dict
            Additional arguments passed to QWidget
        """
        super().__init__(**kwargs)
        print(f"Initializing PVControl for model: {model.label}")
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

        # Fixed-width input field
        self.edit = QLineEdit("")
        self.edit.setFixedWidth(100)
        self.edit.setFixedHeight(20)
        self.edit.setAlignment(Qt.AlignRight)

        # Set up input validation based on value_type
        if model.value_type is float:
            self.edit.setValidator(QDoubleValidator())
        elif model.value_type is int:
            self.edit.setValidator(QIntValidator())

        if model.units is not None:
            self.units = model.units
        else:
            self.units = ""

        # Fixed-width set button
        self.setButton = QPushButton("Set")
        self.setButton.setFixedWidth(60)
        self.setButton.setFixedHeight(20)
        self.setButton.clicked.connect(self.enter_value)

        box.addWidget(self.value)
        box.addWidget(self.edit)
        box.addWidget(self.setButton)

        if orientation == "h":
            box.setAlignment(Qt.AlignVCenter)

        self.model.valueChanged.connect(self.setText)
        print(f"[{self.model.name}] PVControl initial setText: {self.model.value}")
        self.setText(self.model.value)
        self.setLayout(box)

    def enter_value(self):
        """Process and validate the entered value before setting."""
        try:
            text = self.edit.text()
            if self.model.value_type is float:
                val = float(text)
            elif self.model.value_type is int:
                val = int(text)
            else:
                val = text
            self.model.set(val)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e), QMessageBox.Ok)

    def setText(self, val):
        """Update the displayed value.

        Parameters
        ----------
        val : str
            Formatted value to display
        """
        if val is None:
            val = "Disconnected"
        self.value.setText(f"{val} {self.units}")


class PVMonitor(QWidget):
    """Monitor a generic PV with fixed-width styling."""

    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        """
        Initialize the monitor widget.

        Parameters
        ----------
        model : object
            The model to monitor.
        parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
        orientation : str, optional
            The orientation of the monitor ('h' or 'v').
        """
        super().__init__(**kwargs)
        print(f"Initializing PVMonitor for model: {model.label}")
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

        if model.units is not None:
            self.units = model.units
        else:
            self.units = ""

        box.addWidget(self.value)

        if orientation == "h":
            box.setAlignment(Qt.AlignVCenter)

        self.model.valueChanged.connect(self.setText)
        print(f"[{self.model.name}] PVMonitor initial setText: {self.model.value}")
        self.setText(self.model.value)
        self.setLayout(box)

    def setText(self, val):
        """Update the displayed value.

        Parameters
        ----------
        val : str
            Formatted value to display
        """
        if val is None:
            val = "Disconnected"
        self.value.setText(f"{val} {self.units}")


class PVMonitorV(PVMonitor):
    def __init__(self, model, **kwargs):
        super().__init__(model, orientation="v", **kwargs)


class PVMonitorH(PVMonitor):
    def __init__(self, model, **kwargs):
        super().__init__(model, orientation="h", **kwargs)


SI_PREFIXES = [
    ("p", 1e-12),
    ("n", 1e-9),
    ("u", 1e-6),
    ("m", 1e-3),
    ("", 1),
    ("k", 1e3),
    ("M", 1e6),
    ("G", 1e9),
]

PREFIX_INDEX = {p: i for i, (p, _) in enumerate(SI_PREFIXES)}


class SIPVMonitor(PVMonitor):
    """
    PVMonitor that formats values with SI prefixes.

    Parameters
    ----------
    model : PVModel
        The model to monitor
    base_unit : str
        The base unit (e.g., 'A', 'V')
    min_prefix : str, optional
        Minimum SI prefix (e.g., 'n', 'm', ''), default is ''
    max_prefix : str, optional
        Maximum SI prefix (e.g., 'A', ''), default is ''
    """

    def __init__(
        self, model, *args, base_unit="", min_prefix="", max_prefix="", **kwargs
    ):
        super().__init__(model, *args, **kwargs)
        self.base_unit = base_unit
        self.min_prefix = min_prefix
        self.max_prefix = max_prefix

    def setText(self, value):
        try:
            val = float(value)
            text = self.format_si(val)
        except Exception:
            text = str(value)
        super().setText(text)

    def format_si(self, value):
        abs_val = abs(value)
        # Find the best prefix within min/max
        min_idx = PREFIX_INDEX.get(self.min_prefix, 0)
        max_idx = PREFIX_INDEX.get(self.max_prefix, len(SI_PREFIXES) - 1)
        best_idx = min_idx
        for i in range(min_idx, max_idx + 1):
            prefix, factor = SI_PREFIXES[i]
            if abs_val < factor * 1000 or i == max_idx:
                best_idx = i
                break
        prefix, factor = SI_PREFIXES[best_idx]
        return f"{value / factor:.3g} {prefix}{self.base_unit}"
