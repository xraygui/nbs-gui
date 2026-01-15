import pprint

from qtpy.QtCore import Signal, Slot
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from bluesky_widgets.qt.run_engine_client import PushButtonMinimumWidth


class QtReRunningPlan(QWidget):
    signal_update_widgets = Signal(bool, object)
    signal_running_item_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        print("Initializing QtReRunningPlan")
        super().__init__(parent)
        self.model = model
        self.run_engine = model.run_engine
        self.user_status = model.user_status

        self._monitor_mode = False

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        # Set background color the same as for disabled window.
        p = self._text_edit.palette()
        p.setColor(QPalette.Base, p.color(QPalette.Disabled, QPalette.Base))
        self._text_edit.setPalette(p)

        self._pb_copy_to_queue = PushButtonMinimumWidth("Copy to Queue")
        self._pb_copy_to_queue.clicked.connect(self._pb_copy_to_queue_clicked)

        self._pb_environment_update = QPushButton("Update Environment")
        self._pb_environment_update.setEnabled(False)
        self._pb_environment_update.clicked.connect(self._pb_environment_update_clicked)

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("RUNNING PLAN"))
        hbox.addStretch(1)
        hbox.addWidget(self._pb_environment_update)
        hbox.addWidget(self._pb_copy_to_queue)
        vbox.addLayout(hbox)
        vbox.addWidget(self._text_edit)
        self.setLayout(vbox)

        self._is_item_running = False
        self._running_item_uid = ""
        self._current_plan_status = "idle"
        self._running_item = None
        self._run_list = []
        self._is_paused = False
        self._update_copy_button_state()

        # Connect to run engine events
        self.run_engine.events.running_item_changed.connect(
            self.on_running_item_changed
        )
        self.signal_running_item_changed.connect(self.slot_running_item_changed)

        self.run_engine.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

        # Connect to plan status updates
        print("Connecting to plan status updates")
        self.plan_status = self.user_status.get_redis_dict("PLAN_STATUS")
        if self.plan_status is not None:
            print("Plan status connecting to signal")
            self._current_plan_status = self.plan_status.get("status", "idle")
            self.plan_status.changed.connect(self.slot_plan_status_changed)

    @property
    def monitor_mode(self):
        return self._monitor_mode

    @monitor_mode.setter
    def monitor_mode(self, monitor):
        self._monitor_mode = bool(monitor)
        self._update_copy_button_state()

    def on_running_item_changed(self, event):
        running_item = event.running_item
        run_list = event.run_list
        self.signal_running_item_changed.emit(running_item, run_list)

    @Slot(object, object)
    def slot_running_item_changed(self, running_item, run_list):
        running_item_uid = running_item.get("item_uid", "")
        is_new_item = running_item_uid != self._running_item_uid
        self._running_item_uid = running_item_uid

        # Store the running item and run list for display
        self._running_item = running_item
        self._run_list = run_list

        # The following logic is implemented:
        #   - always scroll to the top of the edit box when the new plan is started.
        #   - don't scroll if contents are changed during execution of a plan unless scroll bar
        #     is all the way down (contents may be changed e.g. during execution of multirun plans)
        #   - if the scroll bar is in the lowest position, then continue scrolling down as text
        #     is added (e.g. UIDs may be added to the list of Run UIDs as multirun plan is executed).
        scroll_value = 0 if is_new_item else self._text_edit.verticalScrollBar().value()
        scroll_maximum = self._text_edit.verticalScrollBar().maximum()
        tb_scrolled_to_bottom = scroll_value and (scroll_value == scroll_maximum)

        # Update the display
        self._update_display()

        self._is_item_running = bool(running_item)
        self._update_copy_button_state()

        scroll_maximum_new = self._text_edit.verticalScrollBar().maximum()
        scroll_value_new = scroll_maximum_new if tb_scrolled_to_bottom else scroll_value
        self._text_edit.verticalScrollBar().setValue(scroll_value_new)

    def on_update_widgets(self, event):
        is_connected = bool(event.is_connected)
        status = event.status
        self.signal_update_widgets.emit(is_connected, status)

    @Slot(bool, object)
    def slot_update_widgets(self, is_connected, status):
        is_connected = bool(is_connected)
        worker_environment_exists = bool(status.get("worker_environment_exists", False))
        manager_state = status.get("manager_state", "idle")
        worker_state = status.get("worker_environment_state", "idle")
        ip_kernel_state = status.get("ip_kernel_state", None)
        monitor_mode = self._monitor_mode

        # Track paused state
        was_paused = self._is_paused
        self._is_paused = manager_state == "paused"

        # Update display if paused state changed
        if was_paused != self._is_paused:
            self._update_display()

        self._pb_environment_update.setEnabled(
            not monitor_mode
            and is_connected
            and worker_environment_exists
            and manager_state in ("idle",)
            and worker_state == "idle"
            and ip_kernel_state != "busy"
        )

        self._update_copy_button_state()

    @Slot()
    def slot_plan_status_changed(self):
        """Handle plan status updates from Redis"""
        plan_status = self.plan_status
        if plan_status and "status" in plan_status:
            self._current_plan_status = plan_status["status"]
            # Update the display to include plan status
            self._update_display()

    def _update_display(self):
        """Update the display with current running item and plan status"""
        s_running_item = ""
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;"

        def _to_html(text, *, nindent=4):
            """Formats text as a sequence indented html lines. Lines are indented by `nindent` spaces"""
            lines = text.split("\n")
            lines_modified = []
            for line in lines:
                line_no_leading_spaces = line.lstrip(" ")
                n_leading_spaces = len(line) - len(line_no_leading_spaces)
                lines_modified.append(
                    "&nbsp;" * (n_leading_spaces + nindent) + line_no_leading_spaces
                )
            text_modified = "<br>".join(lines_modified)

            return text_modified

        # Add paused state at the top if paused
        if self._is_paused:
            s_running_item += "<table width='100%'><tr><td align='center'><span style='color: red; font-size: 16px; font-weight: bold;'>Plan Paused</span></td></tr></table>"

        # Add plan status if not idle AND there's a running item
        if self._current_plan_status != "idle" and self._running_item:
            s_running_item += f"<b>Plan Status:</b> {self._current_plan_status}<br>"

        if self._running_item:
            s_running_item += (
                f"<b>Plan Name:</b> {self._running_item.get('name', '')}<br>"
            )
            if ("args" in self._running_item) and self._running_item["args"]:
                s_running_item += (
                    f"<b>Arguments:</b> {str(self._running_item['args'])[1:-1]}<br>"
                )
            if ("kwargs" in self._running_item) and self._running_item["kwargs"]:
                s_running_item += "<b>Parameters:</b><br>"
                for k, v in self._running_item["kwargs"].items():
                    s_running_item += indent + f"<b>{k}:</b> {v}<br>"

            if ("meta" in self._running_item) and self._running_item["meta"]:
                # This representation of metadata may not be the best, but it is still reasonable.
                #   Note, that metadata may be a dictionary or a list of dictionaries.
                s_meta = pprint.pformat(self._running_item["meta"])
                s_meta = _to_html(s_meta)
                s_running_item += f"<b>Metadata:</b><br>{s_meta}<br>"

        s_run_list = "<b>Runs:</b><br>" if self._run_list else ""
        for run_info in self._run_list:
            run_uid = run_info["uid"]
            run_is_open = run_info["is_open"]
            run_exit_status = run_info["exit_status"]
            s_run = indent + f"{run_uid}  "
            if run_is_open:
                s_run += "In progress ..."
            else:
                s_run += f"Exit status: {run_exit_status}"
            s_run_list += s_run + "<br>"

        self._text_edit.setHtml(s_running_item + s_run_list)

    def _update_copy_button_state(self):
        is_plan_running = self._is_item_running
        monitor_mode = self._monitor_mode
        self._pb_copy_to_queue.setEnabled(is_plan_running and not monitor_mode)

    def _pb_copy_to_queue_clicked(self):
        try:
            self.model.running_item_add_to_queue()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_environment_update_clicked(self):
        try:
            self.model.environment_update()
        except Exception as ex:
            print(f"Exception: {ex}")
