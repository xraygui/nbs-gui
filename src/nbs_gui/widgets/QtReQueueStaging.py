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
from .QtRePlanQueueBase import QtReActiveQueue


class QtReQueueStaging(QtReActiveQueue):

    def __init__(self, model, queue_model=None, parent=None):
        if queue_model is None:
            self.queue_model = model.queue_staging
        else:
            self.queue_model = queue_model

        print("DEBUG: QtReQueueStaging - __init__")
        super().__init__(model, parent=parent)
        print("DEBUG: QtReQueueStaging - __init__ done")

    def _create_buttons(self):
        print("DEBUG: QtReQueueStaging - creating buttons")
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
        print("DEBUG: QtReQueueStaging - creating layout")
        """Create layout specific to queue staging."""
        self._group_box = QGroupBox("Queue Staging")

        vbox = QVBoxLayout()

        header_hbox = QHBoxLayout()
        header_hbox.addWidget(QLabel("STAGING"))
        header_hbox.addStretch(1)

        header_vbox = QVBoxLayout()
        # First row of buttons
        hbox1 = QHBoxLayout()
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
        hbox2.addWidget(self._pb_move_selected_to_queue)
        hbox2.addWidget(self._pb_move_all_to_queue)
        hbox2.addStretch(1)
        hbox2.addWidget(self._pb_copy_selected_to_queue)
        hbox2.addWidget(self._pb_copy_all_to_queue)

        header_vbox.addLayout(hbox1)
        header_vbox.addLayout(hbox2)

        header_hbox.addLayout(header_vbox)
        vbox.addLayout(header_hbox)
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

    def _pb_move_selected_to_queue_clicked(self):
        try:
            selected_plans = self.queue_model.selected_plans
            if selected_plans:
                # Add to main queue
                for plan in selected_plans:
                    self.run_engine.queue_item_add(item=plan)
                # Remove from staging
                self.queue_model.queue_items_remove()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_move_all_to_queue_clicked(self):
        try:
            all_plans = self.queue_model.staged_plans
            if all_plans:
                # Add all to main queue
                for plan in all_plans:
                    self.run_engine.queue_item_add(item=plan)
                # Clear staging
                self.queue_model.queue_clear()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_copy_selected_to_queue_clicked(self):
        try:
            selected_plans = self.queue_model.selected_plans
            if selected_plans:
                # Add to main queue without removing from staging
                for plan in selected_plans:
                    self.run_engine.queue_item_add(item=plan)
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_copy_all_to_queue_clicked(self):
        try:
            all_plans = self.queue_model.staged_plans
            if all_plans:
                # Add all to main queue without removing from staging
                for plan in all_plans:
                    self.run_engine.queue_item_add(item=plan)
        except Exception as ex:
            print(f"Exception: {ex}")
