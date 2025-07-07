import copy

from qtpy.QtCore import Qt, QTimer, Signal, Slot, QMimeData
from qtpy.QtGui import QBrush, QColor, QFontMetrics, QIntValidator, QPalette
from qtpy.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import json


class QueueTableWidget(QTableWidget):
    signal_drop_event = Signal(int, int)
    signal_scroll = Signal(str)
    signal_resized = Signal()

    def __init__(self, plan_queue_items=None):
        super().__init__()
        self.plan_queue_items = plan_queue_items or []
        self._is_mouse_pressed = False
        self._is_scroll_active = False
        self._scroll_direction = ""

        self._scroll_timer_count = 0
        # Duration of period of the first series of events, ms
        self._scroll_timer_period_1 = 200
        # Duration of period of the remaining events, ms
        self._scroll_timer_period_2 = 100
        self._scroll_timer_n_events = 4  # The number of events in the first period
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self._on_scroll_timeout)

    def set_plan_queue_items(self, items):
        """Set the plan queue items for MIME data generation."""
        self.plan_queue_items = items

    def mimeData(self, indexes):
        """Override to provide custom MIME data for drag operations."""
        if not indexes:
            return None

        # Get unique rows from selected indexes
        selected_rows = set(idx.row() for idx in indexes)

        # Get the plan data for each selected row
        plans = []
        for row in sorted(selected_rows):
            if 0 <= row < len(self.plan_queue_items):
                plan = self.plan_queue_items[row]
                plans.append(plan)

        if not plans:
            return None

        mime_data = QMimeData()
        json_data = json.dumps(plans).encode("utf-8")
        mime_data.setData("application/x-bluesky-plan", json_data)
        return mime_data

    def dropEvent(self, event):
        self.deactivate_scroll()
        row, col = -1, -1
        if (event.source() == self) and self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(event.pos()):
                index = self.rootIndex()
            row = index.row()
            col = index.column()

        self.signal_drop_event.emit(row, col)

    def dragMoveEvent(self, event):
        # 'rowHeight(0)' will return 0 if the table is empty,
        #    but we don't need to scroll the empty table
        scroll_activation_area = int(self.rowHeight(0) / 2)

        y = event.pos().y()
        if y < scroll_activation_area:
            self.activate_scroll("up")
        elif y > self.viewport().height() - scroll_activation_area:
            self.activate_scroll("down")
        else:
            self.deactivate_scroll()

    def dragLeaveEvent(self, event):
        self.deactivate_scroll()

    def activate_scroll(self, str):
        if str not in ("up", "down"):
            return

        if not self._is_scroll_active or self._scroll_direction != str:
            self._is_scroll_active = True
            self._scroll_direction = str
            self._scroll_timer_count = 0
            # The period before the first scroll event should be very short
            self._scroll_timer.start(20)

    def deactivate_scroll(self):
        if self._is_scroll_active:
            self._is_scroll_active = False
            self._scroll_direction = ""
            self._scroll_timer.stop()

    def _on_scroll_timeout(self):
        self.signal_scroll.emit(self._scroll_direction)

        self._scroll_timer_count += 1
        timeout = (
            self._scroll_timer_period_1
            if self._scroll_timer_count <= self._scroll_timer_n_events
            else self._scroll_timer_period_2
        )
        self._scroll_timer.start(timeout)


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


class QtRePlanQueue(QWidget):
    signal_update_widgets = Signal(bool)
    signal_update_selection = Signal(object)
    signal_plan_queue_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._monitor_mode = False

        # Set True to block processing of table selection change events
        self._block_table_selection_processing = False

        self._registered_item_editors = []

        # Local copy of the plan queue items for operations performed locally
        #   in the Qt Widget code without calling the model. Using local copy that
        #   precisely matches the contents displayed in the table is more reliable
        #   for local operations (e.g. calling editor when double-clicking the row).
        self._plan_queue_items = []

        self._table_column_labels = (
            "",
            "Name",
            "Parameters",
            "USER",
            "GROUP",
        )
        self._table = QueueTableWidget()
        self._table.setColumnCount(len(self._table_column_labels))
        self._table.setHorizontalHeaderLabels(self._table_column_labels)
        self._table.horizontalHeader().setSectionsMovable(True)

        self._table.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableWidget.ContiguousSelection)

        self._table.setDragEnabled(False)
        self._table.setAcceptDrops(False)
        self._table.setDropIndicatorShown(True)
        self._table.setShowGrid(True)

        # Prevents horizontal autoscrolling when clicking on an item (column) that
        # doesn't fit horizontally the displayed view of the table (annoying behavior)
        self._table.setAutoScroll(False)

        self._table.setAlternatingRowColors(True)

        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setMinimumSectionSize(5)

        self._table_scrolled_to_bottom = False

        # The following parameters are used only to control widget state (e.g. activate/deactivate
        #   buttons), not to perform real operations.
        self._n_table_items = 0  # The number of items in the table
        self._selected_items_pos = []  # Selected items (list of table rows)

        self._pb_move_up = PushButtonMinimumWidth("Up")
        self._pb_move_down = PushButtonMinimumWidth("Down")
        self._pb_move_to_top = PushButtonMinimumWidth("Top")
        self._pb_move_to_bottom = PushButtonMinimumWidth("Bottom")
        self._pb_delete_plan = PushButtonMinimumWidth("Delete")
        self._pb_duplicate_plan = PushButtonMinimumWidth("Duplicate")
        self._pb_clear_queue = PushButtonMinimumWidth("Clear")
        self._pb_deselect = PushButtonMinimumWidth("Deselect")
        self._pb_loop_on = PushButtonMinimumWidth("Loop")
        self._pb_loop_on.setCheckable(True)

        self._pb_move_up.clicked.connect(self._pb_move_up_clicked)
        self._pb_move_down.clicked.connect(self._pb_move_down_clicked)
        self._pb_move_to_top.clicked.connect(self._pb_move_to_top_clicked)
        self._pb_move_to_bottom.clicked.connect(self._pb_move_to_bottom_clicked)
        self._pb_delete_plan.clicked.connect(self._pb_delete_plan_clicked)
        self._pb_duplicate_plan.clicked.connect(self._pb_duplicate_plan_clicked)
        self._pb_clear_queue.clicked.connect(self._pb_clear_queue_clicked)
        self._pb_deselect.clicked.connect(self._pb_deselect_clicked)
        self._pb_loop_on.clicked.connect(self._pb_loop_on_clicked)

        self._group_box = QGroupBox("Plan Queue")
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("QUEUE"))
        hbox.addStretch(1)
        hbox.addWidget(self._pb_move_up)
        hbox.addWidget(self._pb_move_down)
        hbox.addWidget(self._pb_move_to_top)
        hbox.addWidget(self._pb_move_to_bottom)
        hbox.addStretch(1)
        hbox.addWidget(self._pb_deselect)
        hbox.addWidget(self._pb_clear_queue)
        hbox.addStretch(1)
        hbox.addWidget(self._pb_loop_on)
        hbox.addStretch(1)
        hbox.addWidget(self._pb_delete_plan)
        hbox.addWidget(self._pb_duplicate_plan)
        vbox.addLayout(hbox)
        vbox.addWidget(self._table)
        self.setLayout(vbox)

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

        self.model.events.plan_queue_changed.connect(self.on_plan_queue_changed)
        self.signal_plan_queue_changed.connect(self.slot_plan_queue_changed)

        self.model.events.queue_item_selection_changed.connect(
            self.on_queue_item_selection_changed
        )
        self.signal_update_selection.connect(self.slot_change_selection)

        self._table.signal_drop_event.connect(self.on_table_drop_event)
        self._table.signal_scroll.connect(self.on_table_scroll_event)

        self._table.itemSelectionChanged.connect(self.on_item_selection_changed)
        self._table.verticalScrollBar().valueChanged.connect(
            self.on_vertical_scrollbar_value_changed
        )
        self._table.verticalScrollBar().rangeChanged.connect(
            self.on_vertical_scrollbar_range_changed
        )
        self._table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)

        self._update_button_states()

    @property
    def monitor_mode(self):
        return self._monitor_mode

    @monitor_mode.setter
    def monitor_mode(self, monitor):
        self._monitor_mode = bool(monitor)
        self._update_widgets()

        if monitor:
            self._table.cellDoubleClicked.disconnect(self._on_table_cell_double_clicked)
        else:
            self._table.cellDoubleClicked.connect(self._on_table_cell_double_clicked)

    @property
    def registered_item_editors(self):
        """
        Returns reference to the list of registered plan editors. The reference is not editable,
        but the items can be added or removed from the list using ``append``, ``pop`` and ``clear``
        methods.

        Editors may be added to the list of registered plan editors by inserting/appending reference
        to a callable. The must accepts dictionary of item parameters as an argument and return
        boolean value ``True`` if the editor accepts the item. When user double-clicks the table row,
        the editors from the list are called one by one until the plan is accepted. The first editor
        that accepts the plan must be activated and allow users to change plan parameters. Typically
        the editors should be registered in the order starting from custom editors designed for
        editing specific plans proceeding to generic editors that will accept any plan that was
        rejected by custom editors.

        Returns
        -------
        list(callable)
            List of references to registered editors. List is empty if no editors are registered.
        """
        return self._registered_item_editors

    def on_update_widgets(self, event):
        # None should be converted to False:
        is_connected = bool(event.is_connected)
        self.signal_update_widgets.emit(is_connected)

    def _update_widgets(self, is_connected=None):
        if is_connected is None:
            is_connected = bool(self.model.re_manager_connected)

        # Disable drops if there is no connection to RE Manager
        self._table.setDragEnabled(is_connected and not self._monitor_mode)
        self._table.setAcceptDrops(is_connected and not self._monitor_mode)

        self._update_button_states()

    @Slot(bool)
    def slot_update_widgets(self, is_connected):
        self._update_widgets(is_connected)

    def _update_button_states(self):
        is_connected = bool(self.model.re_manager_connected)
        status = self.model.re_manager_status
        loop_mode_on = status["plan_queue_mode"]["loop"] if status else False
        mon = self._monitor_mode

        n_items = self._n_table_items
        selected_items_pos = self._selected_items_pos

        is_sel = len(selected_items_pos) > 0
        sel_top = len(selected_items_pos) and (selected_items_pos[0] == 0)
        sel_bottom = len(selected_items_pos) and (selected_items_pos[-1] == n_items - 1)

        self._pb_move_up.setEnabled(is_connected and not mon and is_sel and not sel_top)
        self._pb_move_down.setEnabled(
            is_connected and not mon and is_sel and not sel_bottom
        )
        self._pb_move_to_top.setEnabled(
            is_connected and not mon and is_sel and not sel_top
        )
        self._pb_move_to_bottom.setEnabled(
            is_connected and not mon and is_sel and not sel_bottom
        )

        self._pb_clear_queue.setEnabled(is_connected and not mon and n_items)
        self._pb_deselect.setEnabled(is_sel)

        self._pb_loop_on.setEnabled(is_connected and not mon)
        self._pb_loop_on.setChecked(loop_mode_on)

        self._pb_delete_plan.setEnabled(is_connected and not mon and is_sel)
        self._pb_duplicate_plan.setEnabled(is_connected and not mon and is_sel)

    def on_vertical_scrollbar_value_changed(self, value):
        max = self._table.verticalScrollBar().maximum()
        self._table_scrolled_to_bottom = value == max

    def on_vertical_scrollbar_range_changed(self, min, max):
        if self._table_scrolled_to_bottom:
            self._table.verticalScrollBar().setValue(max)

    def on_table_drop_event(self, row, col):
        # If the selected queue item is not in the table anymore (e.g. sent to execution),
        #   then ignore the drop event, since the item can not be moved.
        if self.model.selected_queue_item_uids:
            uid_ref_item = self.model.queue_item_pos_to_uid(row)
            try:
                self.model.queue_items_move_in_place_of(uid_ref_item)
            except Exception as ex:
                print(f"Exception: {ex}")

        self._update_button_states()

    def on_table_scroll_event(self, scroll_direction):
        v = self._table.verticalScrollBar().value()
        v_max = self._table.verticalScrollBar().maximum()
        if scroll_direction == "up" and v > 0:
            v_new = v - 1
        elif scroll_direction == "down" and v < v_max:
            v_new = v + 1
        else:
            v_new = v
        if v != v_new:
            self._table.verticalScrollBar().setValue(v_new)

    def on_plan_queue_changed(self, event):
        plan_queue_items = event.plan_queue_items
        selected_item_uids = event.selected_item_uids
        self.signal_plan_queue_changed.emit(plan_queue_items, selected_item_uids)

    @Slot(object, object)
    def slot_plan_queue_changed(self, plan_queue_items, selected_item_uids):
        # Check if the vertical scroll bar is scrolled to the bottom. Ignore the case
        #   when 'scroll_value==0': if the top plan is visible, it should remain visible
        #   even if additional plans are added to the queue.
        self._block_table_selection_processing = True

        # Create local copy of the plan queue items for operations performed locally
        #   within the widget without involving the model.
        self._plan_queue_items = copy.deepcopy(plan_queue_items)

        self._table.set_plan_queue_items(self._plan_queue_items)

        scroll_value = self._table.verticalScrollBar().value()
        scroll_maximum = self._table.verticalScrollBar().maximum()
        self._table_scrolled_to_bottom = scroll_value and (
            scroll_value == scroll_maximum
        )

        self._table.clearContents()
        self._table.setRowCount(len(plan_queue_items))

        if len(plan_queue_items):
            resize_mode = QHeaderView.ResizeToContents
        else:
            # Empty table, stretch the header
            resize_mode = QHeaderView.Stretch
        self._table.horizontalHeader().setSectionResizeMode(resize_mode)

        for nr, item in enumerate(plan_queue_items):
            for nc, col_name in enumerate(self._table_column_labels):
                try:
                    value = self.model.get_item_value_for_label(
                        item=item, label=col_name
                    )
                except KeyError:
                    value = ""
                table_item = QTableWidgetItem(value)
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(nr, nc, table_item)

        # Update the number of table items
        self._n_table_items = len(plan_queue_items)

        # Advance scrollbar if the table is scrolled all the way down.
        if self._table_scrolled_to_bottom:
            scroll_maximum_new = self._table.verticalScrollBar().maximum()
            self._table.verticalScrollBar().setValue(scroll_maximum_new)

        self._block_table_selection_processing = False

        self.slot_change_selection(selected_item_uids)
        self._update_button_states()

    def on_item_selection_changed(self):
        """
        The handler for ``item_selection_changed`` signal emitted by QTableWidget
        """
        if self._block_table_selection_processing:
            return

        sel_rows = self._table.selectionModel().selectedRows()
        try:
            if len(sel_rows) >= 1:
                selected_item_pos = [_.row() for _ in sel_rows]
                selected_item_uids = [
                    self.model.queue_item_pos_to_uid(_) for _ in selected_item_pos
                ]
                self.model.selected_queue_item_uids = selected_item_uids
                self._selected_items_pos = selected_item_pos
            else:
                raise Exception()
        except Exception:
            self.model.selected_queue_item_uids = []
            self._selected_items_pos = []

    def on_queue_item_selection_changed(self, event):
        """
        The handler for the event generated by the model
        """
        selected_item_uids = event.selected_item_uids
        self.signal_update_selection.emit(selected_item_uids)

    @Slot(object)
    def slot_change_selection(self, selected_item_uids):
        rows = [self.model.queue_item_uid_to_pos(_) for _ in selected_item_uids]

        # Keep horizontal scroll value while the selection is changed (more consistent behavior)
        scroll_value = self._table.horizontalScrollBar().value()

        if not rows:
            self._table.clearSelection()
            self._selected_items_pos = []
        else:
            self._block_table_selection_processing = True
            self._table.clearSelection()
            for row in rows:
                if self._table.currentRow() not in rows:
                    self._table.setCurrentCell(rows[-1], 0)
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item:
                        item.setSelected(True)
                    else:
                        print(
                            f"Plan Queue Table: attempting to select non-existing item: row={row} col={col}"
                        )

            row_visible = rows[-1]
            item_visible = self._table.item(row_visible, 0)
            self._table.scrollToItem(item_visible, QAbstractItemView.EnsureVisible)
            self._block_table_selection_processing = False

            self._selected_items_pos = rows

        self._table.horizontalScrollBar().setValue(scroll_value)

        self.model.selected_queue_item_uids = selected_item_uids
        self._update_button_states()

    def _on_table_cell_double_clicked(self, n_row, n_col):
        """
        Double-clicking of an item of the table widget opens the item in Plan Editor.
        """
        # We use local copy of the queue here
        try:
            queue_item = self._plan_queue_items[n_row]
        except IndexError:
            queue_item = None
        registered_editors = self.registered_item_editors

        # Do nothing if item is not found or there are no registered editors
        if not queue_item or not registered_editors:
            return

        item_accepted = False
        for editor_activator in registered_editors:
            try:
                item_accepted = editor_activator(queue_item)
            except Exception:
                print(f"Editor failed to start for the item {queue_item['name']}")

            if item_accepted:
                break

        if not item_accepted:
            print(f"Item {queue_item['name']!r} was rejected by all registered editors")

    def _pb_move_up_clicked(self):
        try:
            self.model.queue_items_move_up()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_down_clicked(self):
        try:
            self.model.queue_items_move_down()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_to_top_clicked(self):
        try:
            self.model.queue_items_move_to_top()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_to_bottom_clicked(self):
        try:
            self.model.queue_items_move_to_bottom()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_delete_plan_clicked(self):
        try:
            self.model.queue_items_remove()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_clear_queue_clicked(self):
        try:
            self.model.queue_clear()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_deselect_clicked(self):
        self._table.clearSelection()

    def _pb_loop_on_clicked(self):
        loop_enable = self._pb_loop_on.isChecked()
        try:
            self.model.queue_mode_loop_enable(loop_enable)
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_duplicate_plan_clicked(self):
        try:
            self.model.queue_item_copy_to_queue()
        except Exception as ex:
            print(f"Exception: {ex}")
