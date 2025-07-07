from qtpy.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel
from qtpy.QtWidgets import (
    QTableWidget,
    QTableView,
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
)
from qtpy.QtCore import Signal, Slot, Qt
from bluesky_widgets.qt.run_engine_client import (
    QueueTableWidget,
    PushButtonMinimumWidth,
)
import copy


class QtReQueueStaging(QWidget):
    signal_update_selection = Signal(object)
    signal_plan_queue_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model.queue_staging
        self.top_level_model = model
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

        # New buttons for queue operations
        self._pb_move_selected_to_queue = PushButtonMinimumWidth(
            "Move Selected to Queue"
        )
        self._pb_move_all_to_queue = PushButtonMinimumWidth("Move All to Queue")
        self._pb_copy_selected_to_queue = PushButtonMinimumWidth(
            "Copy Selected to Queue"
        )
        self._pb_copy_all_to_queue = PushButtonMinimumWidth("Copy All to Queue")

        self._pb_move_up.clicked.connect(self._pb_move_up_clicked)
        self._pb_move_down.clicked.connect(self._pb_move_down_clicked)
        self._pb_move_to_top.clicked.connect(self._pb_move_to_top_clicked)
        self._pb_move_to_bottom.clicked.connect(self._pb_move_to_bottom_clicked)
        self._pb_delete_plan.clicked.connect(self._pb_delete_plan_clicked)
        self._pb_duplicate_plan.clicked.connect(self._pb_duplicate_plan_clicked)
        self._pb_clear_queue.clicked.connect(self._pb_clear_queue_clicked)
        self._pb_deselect.clicked.connect(self._pb_deselect_clicked)

        # Connect new button signals
        self._pb_move_selected_to_queue.clicked.connect(
            self._pb_move_selected_to_queue_clicked
        )
        self._pb_move_all_to_queue.clicked.connect(self._pb_move_all_to_queue_clicked)
        self._pb_copy_selected_to_queue.clicked.connect(
            self._pb_copy_selected_to_queue_clicked
        )
        self._pb_copy_all_to_queue.clicked.connect(self._pb_copy_all_to_queue_clicked)

        self._group_box = QGroupBox("Plan Queue")
        vbox = QVBoxLayout()

        # First row - staging operations
        hbox1 = QHBoxLayout()
        hbox1.addWidget(QLabel("STAGING"))
        hbox1.addStretch(1)
        hbox1.addWidget(self._pb_move_up)
        hbox1.addWidget(self._pb_move_down)
        hbox1.addWidget(self._pb_move_to_top)
        hbox1.addWidget(self._pb_move_to_bottom)
        hbox1.addStretch(1)
        hbox1.addWidget(self._pb_deselect)
        hbox1.addWidget(self._pb_clear_queue)
        hbox1.addStretch(1)
        hbox1.addWidget(self._pb_delete_plan)
        hbox1.addWidget(self._pb_duplicate_plan)

        # Second row - queue operations
        hbox2 = QHBoxLayout()
        hbox2.addWidget(QLabel("QUEUE OPS"))
        hbox2.addStretch(1)
        hbox2.addWidget(self._pb_move_selected_to_queue)
        hbox2.addWidget(self._pb_move_all_to_queue)
        hbox2.addStretch(1)
        hbox2.addWidget(self._pb_copy_selected_to_queue)
        hbox2.addWidget(self._pb_copy_all_to_queue)
        # hbox2.addStretch(1)

        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addWidget(self._table)
        self.setLayout(vbox)

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
        self._update_widgets()

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

    def _update_widgets(self, is_connected=None):
        """Update widget state - simplified for staging without connection requirements."""
        # Enable drag and drop for staging
        self._table.setDragEnabled(True)
        self._table.setAcceptDrops(True)
        self._update_button_states()

    def _update_button_states(self):
        """Update button states based on selection and queue state."""
        mon = self._monitor_mode

        n_items = self._n_table_items
        selected_items_pos = self._selected_items_pos

        is_sel = len(selected_items_pos) > 0
        sel_top = len(selected_items_pos) and (selected_items_pos[0] == 0)
        sel_bottom = len(selected_items_pos) and (selected_items_pos[-1] == n_items - 1)

        self._pb_move_up.setEnabled(not mon and is_sel and not sel_top)
        self._pb_move_down.setEnabled(not mon and is_sel and not sel_bottom)
        self._pb_move_to_top.setEnabled(not mon and is_sel and not sel_top)
        self._pb_move_to_bottom.setEnabled(not mon and is_sel and not sel_bottom)

        self._pb_clear_queue.setEnabled(not mon and n_items)
        self._pb_deselect.setEnabled(is_sel)

        self._pb_delete_plan.setEnabled(not mon and is_sel)
        self._pb_duplicate_plan.setEnabled(not mon and is_sel)

        # Queue operation buttons
        self._pb_move_selected_to_queue.setEnabled(not mon and is_sel)
        self._pb_move_all_to_queue.setEnabled(not mon and n_items)
        self._pb_copy_selected_to_queue.setEnabled(not mon and is_sel)
        self._pb_copy_all_to_queue.setEnabled(not mon and n_items)

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

    def _pb_duplicate_plan_clicked(self):
        try:
            self.model.queue_item_copy_to_queue()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_selected_to_queue_clicked(self):
        """Move selected items from staging to main queue."""
        selected_uids = self.model.selected_queue_item_uids
        if not selected_uids:
            return

        try:
            # Get selected items from staging
            selected_items = []
            for uid in selected_uids:
                item = self.model.queue_item_by_uid(uid)
                if item:
                    selected_items.append(item)

            # Add to main queue
            for item in selected_items:
                self.top_level_model.run_engine.queue_item_add(item=item)

            # Remove from staging
            self.model.queue_items_remove()

        except Exception as ex:
            print(f"Exception moving selected to queue: {ex}")

    def _pb_move_all_to_queue_clicked(self):
        """Move all items from staging to main queue."""
        try:
            # Get all items from staging
            all_items = []
            for item in self.model.staged_plans:
                all_items.append(item)

            # Add to main queue
            for item in all_items:
                self.top_level_model.run_engine.queue_item_add(item=item)

            # Clear staging
            self.model.queue_clear()

        except Exception as ex:
            print(f"Exception moving all to queue: {ex}")

    def _pb_copy_selected_to_queue_clicked(self):
        """Copy selected items from staging to main queue."""
        selected_uids = self.model.selected_queue_item_uids
        if not selected_uids:
            return

        try:
            # Get selected items from staging
            for uid in selected_uids:
                item = self.model.queue_item_by_uid(uid)
                if item:
                    # Copy to main queue (don't remove from staging)
                    self.top_level_model.run_engine.queue_item_add(item=item)

        except Exception as ex:
            print(f"Exception copying selected to queue: {ex}")

    def _pb_copy_all_to_queue_clicked(self):
        """Copy all items from staging to main queue."""
        try:
            # Get all items from staging
            for item in self.model.staged_plans:
                # Copy to main queue (don't remove from staging)
                self.top_level_model.run_engine.queue_item_add(item=item)

        except Exception as ex:
            print(f"Exception copying all to queue: {ex}")
