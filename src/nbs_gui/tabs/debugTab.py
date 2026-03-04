"""
Debugging tab for inspecting runtime state of the Qt application.
"""

from __future__ import annotations

from qtpy.QtCore import QTimer
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QLabel,
)

from ..utils.debug_utils import (
    dump_timer_stats,
    dump_object_counts,
    dump_memory_stats,
    dump_widget_stats,
    dump_process_info,
    dump_full_snapshot,
    dump_referrers_summary,
    dump_referrers_aggregate,
)
from ..widgets.simpleConsoleMonitor import QtReConsoleMonitor


def _format_block(title: str, body: str) -> str:
    """
    Format a titled text block for display.

    Parameters
    ----------
    title : str
        Section title.
    body : str
        Section body.

    Returns
    -------
    str
        Formatted block as plain text.
    """

    return f"--- {title} ---\n{body}"


class DebugOutputModel:
    """
    Minimal model for feeding text output into ``QtReConsoleMonitor``.

    Notes
    -----
    ``QtReConsoleMonitor`` expects a model with the following methods:

    - ``start_console_output_monitoring()``
    - ``stop_console_output_monitoring()``
    - ``console_monitoring_thread()``
    """

    def start_console_output_monitoring(self) -> None:
        """
        Start monitoring.

        Returns
        -------
        None
        """

        return None

    def stop_console_output_monitoring(self) -> None:
        """
        Stop monitoring.

        Returns
        -------
        None
        """

        return None

    def console_monitoring_thread(self):
        """
        Return no data.

        Returns
        -------
        None
            No output is produced by this model.
        """

        return None


class DebugTab(QWidget):
    """
    A GUI tab for runtime debugging and diagnostics.
    """

    name = "Debug"
    reloadable = True

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

        self._console = QtReConsoleMonitor(
            DebugOutputModel(),
            parent=self,
            start_monitoring=False,
        )

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(False)
        self._auto_timer.timeout.connect(self._emit_full_snapshot)

        root = QVBoxLayout()
        root.addWidget(self._build_controls())
        root.addWidget(self._console)
        self.setLayout(root)

        self._append(_format_block("Process Info", dump_process_info()))

    def _append(self, text: str) -> None:
        """
        Append text to the output stream.

        Parameters
        ----------
        text : str
            Text to append.

        Returns
        -------
        None
        """

        msg = text.rstrip()
        if not msg:
            return
        edit = self._console._text_edit
        cursor = QTextCursor(edit.document())
        cursor.movePosition(QTextCursor.End)
        if edit.document().isEmpty():
            cursor.insertText(msg)
        else:
            cursor.insertText("\n\n" + msg)
        edit.setTextCursor(cursor)
        edit.ensureCursorVisible()

    def _build_controls(self) -> QWidget:
        """
        Build the controls panel.

        Returns
        -------
        QWidget
            Control panel widget.
        """

        group = QGroupBox("Diagnostics")
        vbox = QVBoxLayout()

        row1 = QHBoxLayout()
        btn_timers = QPushButton("Count Active Qt Timers")
        btn_timers.clicked.connect(self._emit_timer_stats)
        btn_objects = QPushButton("Python Object Counts")
        btn_objects.clicked.connect(self._emit_object_counts)
        btn_memory = QPushButton("Memory Stats")
        btn_memory.clicked.connect(self._emit_memory_stats)
        row1.addWidget(btn_timers)
        row1.addWidget(btn_objects)
        row1.addWidget(btn_memory)

        row2 = QHBoxLayout()
        btn_widgets = QPushButton("Widget Stats")
        btn_widgets.clicked.connect(self._emit_widget_stats)
        btn_process = QPushButton("Process Info")
        btn_process.clicked.connect(self._emit_process_info)
        btn_snapshot = QPushButton("Full Snapshot")
        btn_snapshot.clicked.connect(self._emit_full_snapshot)
        btn_clear = QPushButton("Clear Output")
        btn_clear.clicked.connect(self._clear_output)
        row2.addWidget(btn_widgets)
        row2.addWidget(btn_process)
        row2.addWidget(btn_snapshot)
        row2.addWidget(btn_clear)

        row3 = QHBoxLayout()
        btn_ref_gw = QPushButton("Referrers: GeneratorWorker")
        btn_ref_gw.clicked.connect(self._emit_referrers_generatorworker)
        btn_ref_fw = QPushButton("Referrers: FunctionWorker")
        btn_ref_fw.clicked.connect(self._emit_referrers_functionworker)
        btn_agg_gw = QPushButton("Aggregate: GeneratorWorker")
        btn_agg_gw.clicked.connect(self._emit_aggregate_generatorworker)
        btn_agg_fw = QPushButton("Aggregate: FunctionWorker")
        btn_agg_fw.clicked.connect(self._emit_aggregate_functionworker)
        row3.addWidget(btn_ref_gw)
        row3.addWidget(btn_ref_fw)
        row3.addWidget(btn_agg_gw)
        row3.addWidget(btn_agg_fw)

        auto_row = QHBoxLayout()
        self._cb_auto = QCheckBox("Auto-refresh every")
        self._cb_auto.stateChanged.connect(self._auto_refresh_changed)
        self._sb_seconds = QSpinBox()
        self._sb_seconds.setRange(5, 600)
        self._sb_seconds.setValue(30)
        self._sb_seconds.valueChanged.connect(self._auto_refresh_interval_changed)
        auto_row.addWidget(self._cb_auto)
        auto_row.addWidget(self._sb_seconds)
        auto_row.addWidget(QLabel("seconds"))
        auto_row.addStretch()

        vbox.addLayout(row1)
        vbox.addLayout(row2)
        vbox.addLayout(row3)
        vbox.addLayout(auto_row)
        group.setLayout(vbox)
        return group

    def _clear_output(self) -> None:
        """
        Clear the output display.

        Returns
        -------
        None
        """

        try:
            self._console._text_edit.clear()
        except Exception:
            pass

    def _auto_refresh_changed(self) -> None:
        """
        Enable/disable auto-refresh.

        Returns
        -------
        None
        """

        enabled = self._cb_auto.isChecked()
        if enabled:
            self._auto_timer.start(int(self._sb_seconds.value() * 1000))
        else:
            if self._auto_timer.isActive():
                self._auto_timer.stop()

    def _auto_refresh_interval_changed(self) -> None:
        """
        Apply updated auto-refresh interval if enabled.

        Returns
        -------
        None
        """

        if self._cb_auto.isChecked():
            self._auto_timer.start(int(self._sb_seconds.value() * 1000))

    def _emit_timer_stats(self) -> None:
        self._append(_format_block("QTimer Stats", dump_timer_stats()))

    def _emit_object_counts(self) -> None:
        self._append(_format_block("Python Object Counts", dump_object_counts()))

    def _emit_memory_stats(self) -> None:
        self._append(_format_block("Memory Stats", dump_memory_stats()))

    def _emit_widget_stats(self) -> None:
        self._append(_format_block("Widget Stats", dump_widget_stats()))

    def _emit_process_info(self) -> None:
        self._append(_format_block("Process Info", dump_process_info()))

    def _emit_full_snapshot(self) -> None:
        self._append(dump_full_snapshot())

    def _emit_referrers_generatorworker(self) -> None:
        self._append(
            _format_block(
                "Referrers: GeneratorWorker",
                dump_referrers_summary("GeneratorWorker", sample=5, ref_limit=75),
            )
        )

    def _emit_referrers_functionworker(self) -> None:
        self._append(
            _format_block(
                "Referrers: FunctionWorker",
                dump_referrers_summary("FunctionWorker", sample=5, ref_limit=75),
            )
        )

    def _emit_aggregate_generatorworker(self) -> None:
        self._append(
            _format_block(
                "Aggregate: GeneratorWorker",
                dump_referrers_aggregate("GeneratorWorker", max_objects=100),
            )
        )

    def _emit_aggregate_functionworker(self) -> None:
        self._append(
            _format_block(
                "Aggregate: FunctionWorker",
                dump_referrers_aggregate("FunctionWorker", max_objects=100),
            )
        )

    def teardown(self) -> None:
        """
        Release resources before tab reload.

        Returns
        -------
        None
        """

        if self._auto_timer.isActive():
            self._auto_timer.stop()
        try:
            self._console.teardown()
        except Exception:
            pass

