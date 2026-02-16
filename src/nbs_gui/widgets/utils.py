from qtpy.QtWidgets import QFrame, QMessageBox, QPushButton
from qtpy.QtWidgets import QWidget, QSizePolicy
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QPainter, QColor


def submit_plan(parent, item):
    """
    Submit a plan item to the run engine client.

    Parameters
    ----------
    parent : QWidget
        The parent widget, with run_engine_client attribute
    item : BPlan
        The plan item to be submitted

    Returns
    -------
    bool
        True if submission was successful, False otherwise
    """
    try:
        parent.run_engine_client.queue_item_add(item=item)
        return True
    except Exception as e:
        QMessageBox.critical(
            parent,
            "Plan Submission Error",
            f"Failed to submit plan: {str(e)}",
            QMessageBox.Ok,
        )
        return False


def execute_plan(parent, run_engine_client, item):
    """
    Execute a plan item immediately in the run engine client.

    Parameters
    ----------
    parent : QWidget
        The parent widget, with run_engine_client attribute
    item : BPlan
        The plan item to be executed

    Returns
    -------
    bool
        True if submission was successful, False otherwise
    """
    try:
        run_engine_client._client.item_execute(item=item)
        return True
    except Exception as e:
        QMessageBox.critical(
            parent,
            "Plan Execution Error",
            f"Failed to execute plan: {str(e)}",
            QMessageBox.Ok,
        )
        return False


class HLine(QFrame):
    """
    Creates a horizontal separator line
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class ConfirmationButton(QPushButton):
    """
    A QPushButton that shows a confirmation dialog before emitting clicked.

    Use as a drop-in replacement for QPushButton. The clicked signal is emitted
    only when the user confirms in the "Are you sure?" dialog.

    Parameters
    ----------
    *args
        Positional arguments passed to QPushButton (e.g., text, parent).
    confirmation_title : str, optional
        Title of the confirmation dialog. Default is "Are you sure?".
    confirmation_text : str, optional
        Message in the confirmation dialog. Default is "Are you sure?".
    **kwargs
        Keyword arguments passed to QPushButton.
    """

    def __init__(
        self,
        *args,
        confirmation_title="Are you sure?",
        confirmation_text="Are you sure?",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._confirmation_title = confirmation_title
        self._confirmation_text = confirmation_text

    def _confirm_and_emit_if_accepted(self):
        reply = QMessageBox.question(
            self,
            self._confirmation_title,
            self._confirmation_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.clicked.emit()

    def mouseReleaseEvent(self, event):
        if self.hitButton(event.pos()):
            self._confirm_and_emit_if_accepted()
            self.setDown(False)
        event.accept()

    def keyReleaseEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self._confirm_and_emit_if_accepted()
            self.setDown(False)
            event.accept()
        else:
            super().keyReleaseEvent(event)


class ByteIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = "grey"
        self.setMinimumSize(QSize(15, 15))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setSizePolicy(sizePolicy)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(self.color))
        painter.drawRect(self.rect())

    def sizeHint(self):
        """
        Suggests an initial size for the widget.
        """
        return QSize(20, 20)

    def setColor(self, color):
        self.color = color
        self.update()  # Trigger a repaint

        class PlaceHolder(QWidget):
            """
            Creates a grey placeholder box with specified dimensions.

            Parameters
            ----------
            width : int
                The width of the placeholder box in pixels.
            height : int
                The height of the placeholder box in pixels.
            parent : Optional[QWidget]
                The parent widget. Default is None.
            """

            def __init__(self, width, height, parent=None):
                super().__init__(parent)
                self.setMinimumSize(QSize(width, height))
                self.setMaximumSize(QSize(width, height))
                self.color = "grey"

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setBrush(QColor(self.color))
                painter.drawRect(self.rect())


class SquareByteIndicator(ByteIndicator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aspectRatio = 1
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)  # Enable heightForWidth
        self.setSizePolicy(sizePolicy)

    def heightForWidth(self, width):
        """
        Ensures the height respects the aspect ratio based on the width.
        """
        return int(width * self.aspectRatio)

    def resizeEvent(self, event):
        """
        Adjusts the size while keeping the aspect ratio fixed.
        """
        newSize = min(self.width(), self.height())
        self.resize(newSize, newSize)
