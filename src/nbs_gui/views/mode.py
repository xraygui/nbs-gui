"""Views for beamline mode control."""

from qtpy.QtWidgets import (
    QWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QFrame,
    QMessageBox,
)
from qtpy.QtCore import Slot

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
            # self.model.set_mode(mode)
