from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import (
    QFont,
    QFontMetrics,
    QPalette,
    QTextCursor,
)
from qtpy.QtWidgets import (
    QPlainTextEdit,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
)
from qtpy.QtGui import QIntValidator
from bluesky_widgets.qt.threading import FunctionWorker


class PushButtonMinimumWidth(QPushButton):
    """
    Push button minimum width necessary to fit the text
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text = self.text()
        font = self.font()

        fm = QFontMetrics(font)
        text_width = fm.width(text) + 6
        self.setFixedWidth(text_width)


class QtReConsoleMonitor(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        # self.setAttribute(Qt.WA_DeleteOnClose)
        print("New QtReConsoleMonitor with QPlainTextEdit")
        self._max_lines = 1000

        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setMaximumBlockCount(self._max_lines)

        p = self._text_edit.palette()
        p.setColor(QPalette.Base, p.color(QPalette.Disabled, QPalette.Base))
        self._text_edit.setPalette(p)

        self._text_edit.setFont(QFont("Monospace"))

        self._text_edit.verticalScrollBar().sliderPressed.connect(self._slider_pressed)
        self._text_edit.verticalScrollBar().sliderReleased.connect(
            self._slider_released
        )
        self._is_slider_pressed = False

        self._pb_clear = PushButtonMinimumWidth("Clear")
        self._pb_clear.clicked.connect(self._pb_clear_clicked)
        self._lb_max_lines = QLabel("Max. Lines:")
        self._le_max_lines = QLineEdit()
        self._le_max_lines.setMaximumWidth(60)
        self._le_max_lines.setAlignment(Qt.AlignHCenter)
        self._le_max_lines.setText(f"{self._max_lines}")
        self._le_max_lines.editingFinished.connect(self._le_max_lines_editing_finished)

        self._le_max_lines_min = 10
        self._le_max_lines_max = 10000
        self._le_max_lines.setValidator(
            QIntValidator(self._le_max_lines_min, self._le_max_lines_max)
        )

        self._autoscroll_enabled = True
        self._cb_autoscroll = QCheckBox("Autoscroll")
        self._cb_autoscroll.setChecked(True)
        self._cb_autoscroll.stateChanged.connect(self._cb_autoscroll_state_changed)

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(self._cb_autoscroll)
        hbox.addStretch()
        hbox.addWidget(self._lb_max_lines)
        hbox.addWidget(self._le_max_lines)
        hbox.addWidget(self._pb_clear)
        vbox.addLayout(hbox)
        vbox.addWidget(self._text_edit)
        self.setLayout(vbox)

        self.model = model
        self.model.start_console_output_monitoring()
        self._start_thread()
        self._start_timer()
        self._stop = False

    def _process_new_console_output(self, result):
        """
        Process new console output and append to text edit.

        Parameters
        ----------
        result : tuple
            Tuple of (time, msg) where time is a timestamp and msg is the console output
        """
        time, msg = result

        # Handle None or empty messages
        if msg is None or not msg:
            return

        # Strip any trailing newlines to prevent doubles
        msg = msg.rstrip("\n")

        # Add the newline explicitly only if we're not at the start
        if self._text_edit.document().isEmpty():
            self._text_edit.insertPlainText(msg)
        else:
            self._text_edit.insertPlainText("\n" + msg)

        if self._autoscroll_enabled and not self._is_slider_pressed:
            self._text_edit.moveCursor(QTextCursor.End)

    def _update_console_output(self):
        """
        Timer callback to update the display
        """
        if not self._stop:
            self._start_timer()

    def _start_timer(self):
        """
        Start the update timer
        """
        QTimer.singleShot(195, self._update_console_output)

    def _slider_pressed(self):
        self._is_slider_pressed = True

    def _slider_released(self):
        self._is_slider_pressed = False

    def _is_slider_at_bottom(self):
        sbar = self._text_edit.verticalScrollBar()
        return sbar.value() == sbar.maximum() and self._autoscroll_enabled

    def _pb_clear_clicked(self):
        self._text_edit.clear()

    def _le_max_lines_editing_finished(self):
        v = int(self._le_max_lines.text())
        v = max(min(v, self._le_max_lines_max), self._le_max_lines_min)
        self._le_max_lines.setText(f"{v}")
        self._max_lines = v
        self._text_edit.setMaximumBlockCount(v)

    def _cb_autoscroll_state_changed(self, state):
        self._autoscroll_enabled = state == Qt.Checked

    def _start_thread(self):
        """
        Start a new thread to monitor console output
        """
        self._thread = FunctionWorker(self.model.console_monitoring_thread)
        self._thread.returned.connect(self._process_new_console_output)
        self._thread.finished.connect(self._finished_receiving_console_output)
        self._thread.start()

    def _finished_receiving_console_output(self):
        """
        Callback when thread finishes - starts a new thread if not stopped
        """
        if not self._stop:
            self._start_thread()
