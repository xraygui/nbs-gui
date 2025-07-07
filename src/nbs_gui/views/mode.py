"""Views for beamline mode control."""

from qtpy.QtWidgets import (
    QWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QFrame,
)
from qtpy.QtCore import Slot


class ModeMonitor(QWidget):
    """Display widget for monitoring beamline mode.

    Parameters
    ----------
    model : ModeModel
        Model containing mode information and state
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    parent : QWidget, optional
        The Qt parent widget.
    """

    def __init__(self, model, parent_model=None, parent=None):
        super().__init__(parent)
        self.model = model

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(4)

        # Mode label
        self.label = QLabel(self.model.label)
        self.label.setFixedHeight(20)
        layout.addWidget(self.label)

        # Current mode display
        self.mode_display = QLabel()
        self.mode_display.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.mode_display.setFixedWidth(100)
        self.mode_display.setFixedHeight(20)
        self.mode_display.setToolTip("Current beamline mode")
        layout.addWidget(self.mode_display)

        self.setLayout(layout)

        # Connect signals
        self.model.mode_changed.connect(self._on_mode_change)

        # Initialize with current mode
        if self.model.current_mode:
            self._on_mode_change(self.model.current_mode)

    @Slot(str)
    def _on_mode_change(self, mode):
        """Update display when mode changes."""
        info = self.model.mode_metadata.get(mode, {})
        display_name = info.get("name", mode)
        description = info.get("description", "")

        self.mode_display.setText(display_name)
        if description:
            self.mode_display.setToolTip(description)


class ModeControl(ModeMonitor):
    """Control widget for changing beamline mode.

    Parameters
    ----------
    model : ModeModel
        Model containing mode information and state
    parent_model : object, optional
        The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
    parent : QWidget, optional
        The Qt parent widget.
    """

    def __init__(self, model, parent_model=None, parent=None):
        super().__init__(model, parent_model=parent_model, parent=parent)

        # Add mode selector after the display
        self.mode_combo = QComboBox()
        self.mode_combo.setFixedHeight(20)

        # Add available modes to combo box
        for mode in self.model.available_modes:
            info = self.model.mode_metadata.get(mode, {})
            display_name = info.get("name", mode)
            self.mode_combo.addItem(display_name, mode)

        # Insert after mode display
        self.layout().insertWidget(2, self.mode_combo)

        # Connect signals
        self.mode_combo.currentIndexChanged.connect(self._on_combo_change)
        self.model.mode_changed.connect(self._update_combo)

        # Initialize combo box state
        if self.model.current_mode:
            self._update_combo(self.model.current_mode)

    def _on_combo_change(self, index):
        """Handle mode selection from combo box."""
        if index >= 0:
            mode = self.mode_combo.currentData()
            self.model.set_mode(mode)

    @Slot(str)
    def _update_combo(self, mode):
        """Update combo box when mode changes externally."""
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
