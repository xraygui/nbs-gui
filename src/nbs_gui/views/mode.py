"""Views for beamline mode control."""

from qtpy.QtWidgets import (
    QWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QPushButton,
    QDialog,
    QFrame,
    QSizePolicy,
)
from qtpy.QtCore import Qt

from nbs_gui.settings import get_top_level_model
from nbs_gui.views.enums import EnumControl
from bluesky_queueserver_api import BFunc



class ModeControl(EnumControl):
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

    def __init__(self, model, parent_model=None, parent=None, **kwargs):
        super().__init__(model, parent_model=parent_model, parent=parent, **kwargs)

        self.run_engine = get_top_level_model().run_engine


    def setValue(self, value):
        """Handle mode selection from combo box."""

        function = BFunc(
            "activate_mode",
            value
        )
        try:
            self.run_engine._client.function_execute(function)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Mode Activation Error",
                f"Failed to activate mode: {str(e)}",
                QMessageBox.Ok,
            )


class ModeChangeDialog(QDialog):
    """Dialog for activating and deactivating Redis-backed modes.

    Parameters
    ----------
    model : RedisModeModel
        Model containing active and available mode state.
    execute_callback : callable
        Function that executes a mode action.
    parent : QWidget, optional
        Qt parent widget.
    """

    def __init__(self, model, execute_callback, parent=None):
        super().__init__(parent=parent)
        self.model = model
        self.execute_callback = execute_callback
        self.setWindowTitle(f"Change {model.label}")

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("Mode Select:"))
        self.mode_combo = QComboBox()
        self.activate_button = QPushButton("Activate")
        self.deactivate_button = QPushButton("Deactivate")
        select_row.addWidget(self.mode_combo, 1)
        select_row.addWidget(self.activate_button)
        select_row.addWidget(self.deactivate_button)
        layout.addLayout(select_row)
        self.setLayout(layout)

        self.model.active_modes_changed.connect(self.set_modes)
        self.model.available_modes_changed.connect(self.set_available_modes)
        self.mode_combo.currentTextChanged.connect(self._update_button_state)
        self.activate_button.clicked.connect(self.activate_selected_mode)
        self.deactivate_button.clicked.connect(self.deactivate_selected_mode)
        self.set_available_modes(self.model.available_modes)
        self.set_modes(self.model.active_modes)

    def set_modes(self, modes):
        """Update button states from active modes.

        Parameters
        ----------
        modes : iterable of str
            Active mode names.
        """
        self._update_button_state()

    def set_available_modes(self, modes):
        """Update selectable mode options.

        Parameters
        ----------
        modes : iterable of str
            Available mode names.
        """
        current_mode = self.mode_combo.currentText()
        mode_names = [str(mode) for mode in modes or []]
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItems(mode_names)
        if current_mode in mode_names:
            self.mode_combo.setCurrentText(current_mode)
        self.mode_combo.blockSignals(False)
        self._update_button_state()

    def activate_selected_mode(self):
        """Request activation for the selected mode."""
        mode = self.mode_combo.currentText().strip()
        if mode:
            self.execute_callback("activate_mode", mode)

    def deactivate_selected_mode(self):
        """Request deactivation for the selected mode."""
        mode = self.mode_combo.currentText().strip()
        if mode:
            self.execute_callback("deactivate_mode", mode)

    def _update_button_state(self):
        mode = self.mode_combo.currentText().strip()
        is_active = mode in self.model.active_modes
        self.activate_button.setEnabled(bool(mode) and not is_active)
        self.deactivate_button.setEnabled(bool(mode) and is_active)


class RedisModeControl(QWidget):
    """Control widget for Redis-backed active modes.

    Parameters
    ----------
    model : RedisModeModel
        Model containing active mode state.
    parent_model : object, optional
        Parent model in the widget/model hierarchy.
    parent : QWidget, optional
        Qt parent widget.
    """

    def __init__(self, model, parent_model=None, parent=None, orientation=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.model = model
        self.run_engine = get_top_level_model().run_engine

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(6)

        self.label = QLabel(model.label)
        self.change_modes_button = QPushButton("Change Modes")
        self.active_modes_label = QLabel()
        self.active_modes_label.setWordWrap(True)
        self.active_modes_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.active_modes_label.setFrameStyle(QFrame.Box)
        self.active_modes_label.setMinimumWidth(100)
        self.active_modes_label.setFixedHeight(20)
        self.active_modes_label.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Fixed,
        )

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.change_modes_button)
        layout.addWidget(self.active_modes_label)
        self.setLayout(layout)

        self.model.active_modes_changed.connect(self.set_modes)
        self.change_modes_button.clicked.connect(self.open_mode_dialog)
        self.set_modes(self.model.active_modes)

    def set_modes(self, modes):
        """Update active mode display.

        Parameters
        ----------
        modes : iterable of str
            Active mode names.
        """
        mode_names = [str(mode) for mode in modes or []]
        mode_text = ", ".join(mode_names)
        self.active_modes_label.setText(mode_text)
        text_width = self.active_modes_label.fontMetrics().horizontalAdvance(mode_text)
        self.active_modes_label.setMinimumWidth(max(100, text_width + 12))

    def open_mode_dialog(self):
        """Open mode activation controls."""
        dialog = ModeChangeDialog(self.model, self._execute_mode_function, parent=self)
        dialog.exec()

    def _execute_mode_function(self, function_name, mode):
        function = BFunc(function_name, mode)
        try:
            self.run_engine._client.function_execute(function)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Mode Error",
                f"Failed to execute {function_name}: {str(e)}",
                QMessageBox.Ok,
            )
