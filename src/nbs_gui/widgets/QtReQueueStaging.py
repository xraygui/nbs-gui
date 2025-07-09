import copy
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTableView,
    QAbstractItemView,
)
from qtpy.QtCore import Signal, Slot, Qt
from bluesky_widgets.qt.run_engine_client import PushButtonMinimumWidth
from .QtRePlanQueue import BaseQueueWidget


class QtReQueueStaging(BaseQueueWidget):
    signal_update_selection = Signal(object)
    signal_plan_queue_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        self.model = model.queue_staging
        self.top_level_model = model
        super().__init__(self.model, parent)

        # Initialize missing attributes
        self._registered_item_editors = []
        self._monitor_mode = False
        self._block_table_selection_processing = False

        # Connect staging-specific signals
        self.model.events.plan_queue_changed.connect(self.on_plan_queue_changed)
        self.signal_plan_queue_changed.connect(self.slot_plan_queue_changed)

        self.model.events.queue_item_selection_changed.connect(
            self.on_queue_item_selection_changed
        )
        self.signal_update_selection.connect(self.slot_change_selection)

    def _create_buttons(self):
        """Create buttons specific to queue staging."""
        # First row of buttons (same as main queue)
        self._pb_move_up = PushButtonMinimumWidth("Up")
        self._pb_move_down = PushButtonMinimumWidth("Down")
        self._pb_move_to_top = PushButtonMinimumWidth("Top")
        self._pb_move_to_bottom = PushButtonMinimumWidth("Bottom")
        self._pb_delete_plan = PushButtonMinimumWidth("Delete")
        self._pb_duplicate_plan = PushButtonMinimumWidth("Duplicate")
        self._pb_clear_queue = PushButtonMinimumWidth("Clear")
        self._pb_deselect = PushButtonMinimumWidth("Deselect")

        # Second row of buttons (staging-specific)
        self._pb_move_selected_to_queue = PushButtonMinimumWidth(
            "Move Selected to Queue"
        )
        self._pb_move_all_to_queue = PushButtonMinimumWidth("Move All to Queue")
        self._pb_copy_selected_to_queue = PushButtonMinimumWidth(
            "Copy Selected to Queue"
        )
        self._pb_copy_all_to_queue = PushButtonMinimumWidth("Copy All to Queue")

        # Connect first row buttons
        self._pb_move_up.clicked.connect(self._pb_move_up_clicked)
        self._pb_move_down.clicked.connect(self._pb_move_down_clicked)
        self._pb_move_to_top.clicked.connect(self._pb_move_to_top_clicked)
        self._pb_move_to_bottom.clicked.connect(self._pb_move_to_bottom_clicked)
        self._pb_delete_plan.clicked.connect(self._pb_delete_plan_clicked)
        self._pb_duplicate_plan.clicked.connect(self._pb_duplicate_plan_clicked)
        self._pb_clear_queue.clicked.connect(self._pb_clear_queue_clicked)
        self._pb_deselect.clicked.connect(self._pb_deselect_clicked)

        # Connect second row buttons
        self._pb_move_selected_to_queue.clicked.connect(
            self._pb_move_selected_to_queue_clicked
        )
        self._pb_move_all_to_queue.clicked.connect(self._pb_move_all_to_queue_clicked)
        self._pb_copy_selected_to_queue.clicked.connect(
            self._pb_copy_selected_to_queue_clicked
        )
        self._pb_copy_all_to_queue.clicked.connect(self._pb_copy_all_to_queue_clicked)

    def _create_layout(self):
        """Create layout specific to queue staging."""
        self._group_box = QGroupBox("Queue Staging")
        vbox = QVBoxLayout()

        # First row of buttons
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

        # Second row of buttons
        hbox2 = QHBoxLayout()
        hbox2.addStretch(1)
        hbox2.addWidget(self._pb_move_selected_to_queue)
        hbox2.addWidget(self._pb_move_all_to_queue)
        hbox2.addStretch(1)
        hbox2.addWidget(self._pb_copy_selected_to_queue)
        hbox2.addWidget(self._pb_copy_all_to_queue)
        hbox2.addStretch(1)

        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addWidget(self._table)
        self.setLayout(vbox)

    def _update_button_states(self):
        """Update button states specific to queue staging."""
        # Simplified for staging without connection requirements
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

        # Second row buttons
        self._pb_move_selected_to_queue.setEnabled(not mon and is_sel)
        self._pb_move_all_to_queue.setEnabled(not mon and n_items)
        self._pb_copy_selected_to_queue.setEnabled(not mon and is_sel)
        self._pb_copy_all_to_queue.setEnabled(not mon and n_items)

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

        # Update the custom table widget with the plan queue items
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
        try:
            selected_plans = self.model.selected_plans
            if selected_plans:
                # Add to main queue
                for plan in selected_plans:
                    self.top_level_model.queue_item_add(item=plan)
                # Remove from staging
                self.model.queue_items_remove()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_all_to_queue_clicked(self):
        try:
            all_plans = self.model.staged_plans
            if all_plans:
                # Add all to main queue
                for plan in all_plans:
                    self.top_level_model.queue_item_add(item=plan)
                # Clear staging
                self.model.queue_clear()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_copy_selected_to_queue_clicked(self):
        try:
            selected_plans = self.model.selected_plans
            if selected_plans:
                # Add to main queue without removing from staging
                for plan in selected_plans:
                    self.top_level_model.queue_item_add(item=plan)
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_copy_all_to_queue_clicked(self):
        try:
            all_plans = self.model.staged_plans
            if all_plans:
                # Add all to main queue without removing from staging
                for plan in all_plans:
                    self.top_level_model.queue_item_add(item=plan)
        except Exception as ex:
            print(f"Exception: {ex}")
