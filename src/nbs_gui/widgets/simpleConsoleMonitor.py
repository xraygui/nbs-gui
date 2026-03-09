from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtGui import (
    QFont,
    QFontMetrics,
    QPalette,
    QTextCursor,
)
from qtpy.QtWidgets import (
    QApplication,
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


class PushButtonMinimumWidth(QPushButton):
    """Push button minimum width necessary to fit the text."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text = self.text()
        font = self.font()

        fm = QFontMetrics(font)
        text_width = fm.width(text) + 6
        self.setFixedWidth(text_width)


class ConsoleMonitorThread(QThread):
    """Thread that polls the RE Manager console output stream.

    Runs a loop calling ``next_msg`` with a short timeout.  When a message
    arrives it is forwarded to the main thread via *message_received*.  The
    loop checks ``_running`` each iteration so it can be stopped
    deterministically with :meth:`stop`.

    Parameters
    ----------
    re_client : RunEngineClient
        The run engine client model whose console monitor to poll.
    parent : QObject, optional
        Parent Qt object.
    """

    message_received = Signal(object, object)

    def __init__(self, re_client, parent=None):
        super().__init__(parent)
        self._re_client = re_client
        self._running = False

    def run(self):
        self._running = True
        client = self._re_client._client
        client.console_monitor.enable()
        while self._running:
            try:
                payload = client.console_monitor.next_msg(timeout=0.2)
                time_val = payload.get("time", None)
                msg = payload.get("msg", None)
                if msg is not None:
                    self.message_received.emit(time_val, msg)
            except client.RequestTimeoutError:
                pass
            except Exception as ex:
                if self._running:
                    print(f"Console monitor error: {ex}")
        try:
            client.console_monitor.disable_wait()
        except Exception:
            pass

    def stop(self):
        """Stop the monitoring loop and wait for the thread to finish."""
        self._running = False
        self.wait(2000)


class QtReConsoleMonitor(QWidget):
    def __init__(self, model, parent=None, start_monitoring=True):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._max_lines = 1000
        self._monitor_thread = None

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
        if start_monitoring:
            self._start_monitoring()

    def _start_monitoring(self):
        """Start the console monitoring thread."""
        self._monitor_thread = ConsoleMonitorThread(self.model, parent=self)
        self._monitor_thread.message_received.connect(self._process_message)
        self._monitor_thread.start()
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.teardown)

    def _process_message(self, time_val, msg):
        """Append a console output message to the text display.

        Parameters
        ----------
        time_val : float or None
            Timestamp of the message.
        msg : str or None
            Console output text.
        """
        if msg is None:
            return
        msg = msg.rstrip()
        if not msg:
            return

        cursor = QTextCursor(self._text_edit.document())
        cursor.movePosition(QTextCursor.End)
        if self._text_edit.document().isEmpty():
            cursor.insertText(msg)
        else:
            cursor.insertText("\n" + msg)
        if self._autoscroll_enabled and not self._is_slider_pressed:
            self._text_edit.setTextCursor(cursor)
            self._text_edit.ensureCursorVisible()

    def _slider_pressed(self):
        self._is_slider_pressed = True

    def _slider_released(self):
        self._is_slider_pressed = False

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

    def teardown(self):
        """Stop monitoring and clean up the thread."""
        if self._monitor_thread is not None:
            self._monitor_thread.stop()
            self._monitor_thread = None
