import ast
import inspect
import copy

from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QRadioButton,
    QButtonGroup,
    QComboBox,
    QCheckBox,
)
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtGui import QBrush, QColor
from .qt_custom import ScrollingComboBox
from bluesky_queueserver import construct_parameters, format_text_descriptions

"""
Copied from bluesky-widgets and modified
"""


class _QtRePlanEditorTable(QTableWidget):
    signal_parameters_valid = Signal(bool)
    signal_item_description_changed = Signal(str)
    # The following signal is emitted only if the cell manually modified
    signal_cell_modified = Signal()

    def __init__(self, model, parent=None, *, editable=False, detailed=True):
        super().__init__(parent)
        self.model = model

        # Colors to display valid and invalid (based on validation) text entries in the table
        self._text_color_valid = QTableWidgetItem().foreground()
        self._text_color_invalid = QBrush(QColor(255, 0, 0))

        self._validation_disabled = False
        self._enable_signal_cell_modified = True

        self._queue_item = None  # Copy of the displayed queue item
        self._params = []
        self._params_indices = []
        self._params_descriptions = {}

        self._item_meta = []
        self._item_result = []

        self._table_column_labels = ("Parameter", "", "Value")
        self.setColumnCount(len(self._table_column_labels))
        self.verticalHeader().hide()

        self.setHorizontalHeaderLabels(self._table_column_labels)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setShowGrid(True)

        self.setAlternatingRowColors(True)

        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setMinimumSectionSize(5)

        self.itemChanged.connect(self.table_item_changed)

        self._editable = editable  # Table is editable
        self._detailed = (
            detailed  # Detailed view of parameters (show all plan parameters)
        )
        self.show_item(item=None)

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, is_editable):
        if self._editable != is_editable:
            self._editable = bool(is_editable)
            self._fill_table()

    @property
    def detailed(self):
        return self._detailed

    @detailed.setter
    def detailed(self, is_detailed):
        if self._detailed != is_detailed:
            self._detailed = bool(is_detailed)
            self._fill_table()

    @property
    def queue_item(self):
        """
        Returns original queue item.
        """
        return self._queue_item

    def get_modified_item(self):
        """
        Returns queue item that was modified during editing.
        """
        return self._params_to_item(self._params, self._queue_item)

    def _clear_table(self):
        self._params = []
        self._params_indices = []
        self.clearContents()
        self.setRowCount(0)

    def _item_to_params(self, item):
        if item is None:
            return [], {}, [], []

        # Get plan parameters (probably should be a function call)
        item_name = item.get("name", None)
        item_type = item.get("item_type", None)
        if item_type in ("plan", "instruction"):
            if item_type == "plan":
                item_params = self.model.get_allowed_plan_parameters(name=item_name)
            else:
                item_params = self.model.get_allowed_instruction_parameters(
                    name=item_name
                )
            item_editable = (item_name is not None) and (item_params is not None)
            params_descriptions = format_text_descriptions(
                item_parameters=item_params, use_html=True
            )
        else:
            raise RuntimeError(f"Unknown item type '{item_type}'")

        item_args, item_kwargs = self.model.get_bound_item_arguments(item)
        if item_args:
            # Failed to bound the arguments. It is likely that the plan can not be submitted
            #   so consider it not editable. Display 'args' as a separate parameter named 'ARGS'.
            item_editable = False
            item_kwargs = dict(**{"ARGS": item_args}, **item_kwargs)

        # print(f"plan_params={pprint.pformat(plan_params)}")
        if item_editable:
            # Construct parameters (list of inspect.Parameter objects)
            parameters = construct_parameters(item_params.get("parameters", {}))
        else:
            parameters = []
            for key, val in item_kwargs.items():
                p = inspect.Parameter(
                    key,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=inspect.Parameter.empty,
                    annotation=inspect.Parameter.empty,
                )
                parameters.append(p)

        params = []
        for p in parameters:
            param_value = (
                item_kwargs[p.name]
                if (p.name in item_kwargs)
                else inspect.Parameter.empty
            )
            is_value_set = (param_value != inspect.Parameter.empty) or (
                p.default == inspect.Parameter.empty
                and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            )

            # description = item_descriptions.get("parameters", {}).get(p.name, None)
            # if not description:
            #     description = f"Description for parameter {p.name} was not found ..."
            params.append(
                {
                    "name": p.name,
                    "value": param_value,
                    "is_value_set": is_value_set,
                    "parameters": p,
                }
            )

        # If metadata exists, it will be displayed after the plan parameters
        meta, item_meta = item.get("meta", {}), []
        if meta:
            if isinstance(meta, list):
                for n, key in enumerate(meta):
                    item_meta.append((f"METADATA {n}", ""))
                    for k, v in key.items():
                        item_meta.append((k, str(v)))
            else:
                item_meta.append(("METADATA", ""))
                for k, v in meta.items():
                    item_meta.append((f"- {k}", str(v)))

        # If results of plan execution exist, they will be displayed after the plan parameters
        result, item_result = item.get("result", {}), []
        if result:
            item_result.append(("RESULT", ""))
            for k, v in result.items():
                item_result.append((f"- {k}", str(v)))

        return params, params_descriptions, item_meta, item_result

    def _params_to_item(self, params, item):
        item = copy.deepcopy(item)

        # Find if there are VAR_POSITIONAL or VAR_KEYWORD arguments with set values
        n_var_pos, n_var_kwd = -1, -1
        for n, p in enumerate(params):
            if p["is_value_set"] and (p["value"] != inspect.Parameter.empty):
                if p["parameters"].kind == inspect.Parameter.VAR_POSITIONAL:
                    n_var_pos = n
                elif p["parameters"].kind == inspect.Parameter.VAR_KEYWORD:
                    n_var_kwd = n

        # Collect 'args'
        args = []
        if n_var_pos >= 0:
            if not isinstance(params[n_var_pos]["value"], (list, tuple)):
                raise ValueError(
                    f"Invalid type of VAR_POSITIONAL argument: {params[n_var_pos]['value']}"
                )
            for n in range(n_var_pos):
                if params[n]["is_value_set"] and (
                    params[n]["value"] != inspect.Parameter.empty
                ):
                    args.append(params[n]["value"])
            args.extend(params[n_var_pos]["value"])

        # Collect 'kwargs'
        n_start = 0 if n_var_pos < 0 else n_var_pos + 1
        n_stop = len(params) if n_var_kwd < 0 else n_var_kwd

        kwargs = {}
        for n in range(n_start, n_stop):
            if params[n]["is_value_set"] and (
                params[n]["value"] != inspect.Parameter.empty
            ):
                kwargs[params[n]["parameters"].name] = params[n]["value"]

        if n_var_kwd >= 0:
            if not isinstance(params[n_var_kwd]["value"], dict):
                raise ValueError(
                    f"Invalid type of VAR_KEYWORD argument: {params[n_var_kwd]['value']}"
                )
            kwargs.update(params[n_var_kwd]["value"])

        item["args"] = args
        item["kwargs"] = kwargs

        return item

    def _show_row_value(self, *, row):
        def print_value(v):
            if isinstance(v, str):
                return f"'{v}'"
            else:
                return str(v)

        p = self._params[row]
        p_name = p["name"]
        value = p["value"]
        default_value = p["parameters"].default
        is_var_positional = p["parameters"].kind == inspect.Parameter.VAR_POSITIONAL
        is_var_keyword = p["parameters"].kind == inspect.Parameter.VAR_KEYWORD
        is_value_set = p["is_value_set"]
        is_optional = (
            (default_value != inspect.Parameter.empty)
            or is_var_positional
            or is_var_keyword
        )
        is_editable = self._editable and (is_value_set or not is_optional)

        description = self._params_descriptions.get("parameters", {}).get(p_name, None)
        if not description:
            description = f"Description for parameter '{p_name}' was not found ..."

        v = value if is_value_set else default_value
        s_value = "" if v == inspect.Parameter.empty else print_value(v)
        if not is_value_set and s_value:
            s_value += " (default)"

        # Set checkable item in column 1
        check_item = QTableWidgetItem()
        check_item.setFlags(check_item.flags() | Qt.ItemIsUserCheckable)
        if not is_optional:
            # Checked and disabled
            check_item.setFlags(check_item.flags() & ~Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked)
        else:
            if self._editable:
                check_item.setFlags(check_item.flags() | Qt.ItemIsEnabled)
            else:
                check_item.setFlags(check_item.flags() & ~Qt.ItemIsEnabled)

            if is_value_set:
                check_item.setCheckState(Qt.Checked)
            else:
                check_item.setCheckState(Qt.Unchecked)

        self.setItem(row, 1, check_item)

        # Set value in column 2
        value_item = QTableWidgetItem(s_value)

        if is_editable:
            value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)
        else:
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)

        if is_value_set:
            value_item.setFlags(value_item.flags() | Qt.ItemIsEnabled)
        else:
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEnabled)

        value_item.setToolTip(description)

        self.setItem(row, 2, value_item)

    def _fill_table(self):
        def print_value(v):
            if isinstance(v, str):
                return f"'{v}'"
            else:
                return str(v)

        self._validation_disabled = True
        self._enable_signal_cell_modified = False
        self.clearContents()

        params = self._params
        params_descriptions = self._params_descriptions
        item_meta = self._item_meta
        item_result = self._item_result

        # By default select all indexes of 'params'
        self._params_indices = list(range(len(params)))
        params_indices = self._params_indices

        # Remove parameters with default values (only when editing is disabled)
        if (not self._editable) and (not self._detailed):
            params_indices.clear()
            for n, p in enumerate(params):
                if p["value"] != inspect.Parameter.empty:
                    params_indices.append(n)

        self.setRowCount(len(params_indices) + len(item_meta) + len(item_result))

        for n, p_index in enumerate(params_indices):
            p = params[p_index]

            is_var_positional = p["parameters"].kind == inspect.Parameter.VAR_POSITIONAL
            is_var_keyword = p["parameters"].kind == inspect.Parameter.VAR_KEYWORD

            key = p["parameters"].name
            value = p["value"]
            default_value = p["parameters"].default

            description = params_descriptions.get("parameters", {}).get(key, None)
            if not description:
                description = (
                    f"Description for parameter '{self._queue_item.get('name', '-')}' "
                    f"was not found ..."
                )

            is_value_set = p["is_value_set"]

            v = value if is_value_set else default_value
            s_value = "" if v == inspect.Parameter.empty else print_value(v)
            if not is_value_set:
                s_value += " (default)"

            key_name = str(key)
            if is_var_positional:
                key_name = f"*{key_name}"
            elif is_var_keyword:
                key_name = f"**{key_name}"
            key_item = QTableWidgetItem(key_name)
            key_item.setToolTip(description)
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(n, 0, key_item)

            self._show_row_value(row=n)

        # Display metadata (if exists)
        n_row = len(params_indices)  # Number of table row
        for k, v in item_meta:
            key_item = QTableWidgetItem(str(k))
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(n_row, 0, key_item)
            value_item = QTableWidgetItem(str(v))
            value_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(n_row, 2, value_item)
            n_row += 1

        # Display results (if exist)
        for k, v in item_result:
            key_item = QTableWidgetItem(str(k))
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(n_row, 0, key_item)
            value_item = QTableWidgetItem(str(v))
            value_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(n_row, 2, value_item)
            n_row += 1

        self._validation_disabled = False
        self._validate_cell_values()
        self._enable_signal_cell_modified = True

    def show_item(self, *, item, editable=None):
        if editable is not None:
            self._editable = bool(editable)

        # Keep the copy of the queue item
        self._queue_item = copy.deepcopy(item)
        self.reset_item()

    def reset_item(self):
        # Generate parameters
        (
            self._params,
            self._params_descriptions,
            self._item_meta,
            self._item_result,
        ) = self._item_to_params(self._queue_item)
        if not self._queue_item:
            self._clear_table()
            description = ""
        else:
            self._fill_table()

            description = self._params_descriptions.get("description", "")
            if not description:
                name = self._queue_item.get("name", "-")
                description = f"Description for the item '{name}' was not found ..."

        # Send the signal that updates item description somewhere else in the code
        self.signal_item_description_changed.emit(description)

    def _validate_cell_values(self):
        """
        Validates each cell in the table that is expected to have manually entered parameters.
        Skips the cells that display the default parameters.

        The function also saves successfully evaluated values to the parameter list.

        Signal is emitted to report results of parameter validation (may be used to
        enable/disable buttons in other widges, e.g. 'Ok' button).
        """
        # Validation may be disabled while the table is being filled.
        if self._validation_disabled:
            return

        data_valid = True
        for n, p_index in enumerate(self._params_indices):
            p = self._params[p_index]
            if p["is_value_set"]:
                table_item = self.item(n, 2)

                if table_item:
                    cell_valid = True
                    cell_text = table_item.text()
                    try:
                        # Currently the simples verification is performed:
                        #   - The cell is evaluated.
                        #   - If the evaluation is successful, then the value is saved.
                        # TODO: verify type of the loaded value whenever possible
                        p["value"] = ast.literal_eval(cell_text)
                    except Exception:
                        cell_valid = False
                        data_valid = False

                    table_item.setForeground(
                        self._text_color_valid
                        if cell_valid
                        else self._text_color_invalid
                    )

        self.signal_parameters_valid.emit(data_valid)

    def table_item_changed(self, table_item):
        try:
            row = self.row(table_item)
            column = self.column(table_item)
            if column == 1:
                is_checked = table_item.checkState() == Qt.Checked
                if self._params[row]["is_value_set"] != is_checked:
                    if (
                        is_checked
                        and self._params[row]["value"] == inspect.Parameter.empty
                    ):
                        self._params[row]["value"] = self._params[row][
                            "parameters"
                        ].default

                    self._params[row]["is_value_set"] = is_checked

                    self._enable_signal_cell_modified = False
                    self._show_row_value(row=row)
                    self._enable_signal_cell_modified = True

            if column in (1, 2):
                self._validate_cell_values()
                if self._enable_signal_cell_modified:
                    self.signal_cell_modified.emit()
        except ValueError:
            pass


class _QtReViewer(QWidget):
    signal_update_widgets = Signal()
    signal_update_selection = Signal(int)
    signal_edit_queue_item = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model.run_engine
        self.top_level_model = model

        self._queue_item_name = ""
        self._queue_item_type = None

        self._lb_item_type = QLabel("Plan:")
        self._lb_item_name_default = "-"
        self._lb_item_name = QLabel(self._lb_item_name_default)
        self._cb_show_optional = QCheckBox("All Parameters")
        self._lb_item_source = QLabel("QUEUE ITEM")

        self._pb_copy_to_queue = QPushButton("Copy to Queue")
        self._pb_add_to_staging = QPushButton("Copy to Staging")
        self._pb_edit = QPushButton("Edit")

        # Start with 'detailed' view (show optional parameters)
        self._wd_editor = _QtRePlanEditorTable(
            self.model, editable=False, detailed=True
        )
        self._cb_show_optional.setCheckState(
            Qt.Checked if self._wd_editor.detailed else Qt.Unchecked
        )

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(self._lb_item_type)
        hbox.addWidget(self._lb_item_name)
        hbox.addStretch(5)
        hbox.addWidget(self._cb_show_optional)
        hbox.addStretch(1)
        hbox.addWidget(self._lb_item_source)
        vbox.addLayout(hbox)

        vbox.addWidget(self._wd_editor)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self._pb_copy_to_queue)
        hbox.addWidget(self._pb_add_to_staging)
        hbox.addWidget(self._pb_edit)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self._cb_show_optional.checkStateChanged.connect(
            self._cb_show_optional_state_changed
        )
        self._pb_copy_to_queue.clicked.connect(self._pb_copy_to_queue_clicked)
        self._pb_add_to_staging.clicked.connect(self._pb_add_to_staging_clicked)
        self._pb_edit.clicked.connect(self._pb_edit_clicked)

        self.model.events.queue_item_selection_changed.connect(
            self.on_queue_item_selection_changed
        )
        self.signal_update_selection.connect(self.slot_change_selection)

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

        self._wd_editor.signal_item_description_changed.connect(
            self.slot_item_description_changed
        )

    def on_queue_item_selection_changed(self, event):
        sel_item_uids = event.selected_item_uids
        # Open item in the viewer only if a single item is selected.
        if len(sel_item_uids) == 1:
            sel_item_uid = sel_item_uids[0]
        else:
            sel_item_uid = ""
        sel_item_pos = self.model.queue_item_uid_to_pos(sel_item_uid)
        self.signal_update_selection.emit(sel_item_pos)

    def on_update_widgets(self, event):
        self.signal_update_widgets.emit()

    @Slot()
    def slot_update_widgets(self):
        self._update_widget_state()

    def _update_widget_state(self):
        item_name = self._queue_item_name
        item_type = self._queue_item_type

        if item_type == "plan":
            is_item_allowed = (
                self.model.get_allowed_plan_parameters(name=item_name) is not None
            )
        elif item_type == "instruction":
            is_item_allowed = (
                self.model.get_allowed_instruction_parameters(name=item_name)
                is not None
            )
        else:
            is_item_allowed = False

        is_connected = bool(self.model.re_manager_connected)

        self._pb_copy_to_queue.setEnabled(is_item_allowed and is_connected)
        self._pb_add_to_staging.setEnabled(is_item_allowed)
        self._pb_edit.setEnabled(is_item_allowed)

    @Slot(str)
    def slot_item_description_changed(self, item_description):
        self._lb_item_name.setToolTip(item_description)

    @Slot(int)
    def slot_change_selection(self, sel_item_pos):
        if sel_item_pos >= 0:
            item = copy.deepcopy(self.model._plan_queue_items[sel_item_pos])
        else:
            item = None
        default_name = self._lb_item_name_default
        self._queue_item_name = item.get("name", default_name) if item else default_name
        self._queue_item_type = item.get("item_type", None) if item else None

        # Displayed item type is supposed to be 'Instruction:' if an instruction is selected,
        #   otherwise it should be 'Plan:' (even if nothing is selected)
        displayed_item_type = (
            "Instruction:" if self._queue_item_type == "instruction" else "Plan:"
        )
        self._lb_item_type.setText(displayed_item_type)

        self._lb_item_name.setText(self._queue_item_name)

        self._update_widget_state()
        self._wd_editor.show_item(item=item)

    def _cb_show_optional_state_changed(self, state):
        is_checked = state == Qt.Checked
        self._wd_editor.detailed = is_checked

    def _pb_copy_to_queue_clicked(self):
        """
        Copy currently selected item to queue.
        """
        try:
            self.model.queue_item_copy_to_queue()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_add_to_staging_clicked(self):
        """
        Add currently selected item to staging queue.
        """
        try:
            # Get the current item from the viewer
            if (
                self._queue_item_name
                and self._queue_item_name != self._lb_item_name_default
            ):
                # Create a copy of the current item
                item = copy.deepcopy(self._wd_editor.queue_item)
                if item:
                    self.top_level_model.queue_staging.queue_item_add(item=item)
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_edit_clicked(self):
        sel_item_uids = self.model.selected_queue_item_uids
        if len(sel_item_uids) == 1:
            sel_item_uid = sel_item_uids[0]
            sel_item = self.model.queue_item_by_uid(sel_item_uid)  # Returns deep copy
            self.signal_edit_queue_item.emit(sel_item)


class _QtReEditor(QWidget):
    signal_update_widgets = Signal()
    signal_switch_tab = Signal(str)
    signal_allowed_plan_changed = Signal()
    signal_update_plan_list = Signal(object)
    signal_update_scan_list = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model.run_engine
        self.top_level_model = model
        self.user_status = model.user_status

        self.user_status.register_signal("PLAN_LIST", self.signal_update_plan_list)
        self.signal_update_plan_list.connect(self._update_plan_list)
        self.user_status.register_signal("SCAN_LIST", self.signal_update_scan_list)
        self.signal_update_scan_list.connect(self._update_scan_list)

        self._queue_item_type = None  # ???
        self._queue_item_name = None  # ???

        self._current_item_type = "plan"
        self._current_plan_name = ""
        self._current_instruction_name = ""
        self._current_item_source = ""  # Values: "", "NEW ITEM", "QUEUE ITEM"
        self._allowed_plan_list = []
        self._allowed_scan_list = []
        self._allowed_instruction_list = []
        self._edit_mode_enabled = False
        self._editor_state_valid = False

        self._ignore_combo_item_list_sel_changed = False

        self._rb_item_scan = QRadioButton("Scan")
        self._rb_item_scan.setChecked(True)
        self._rb_item_plan = QRadioButton("Plan")
        self._rb_item_all = QRadioButton("All Plans")
        self._rb_item_instruction = QRadioButton("Instruction")
        self._grp_item_type = QButtonGroup()
        self._grp_item_type.addButton(self._rb_item_scan)
        self._grp_item_type.addButton(self._rb_item_all)
        self._grp_item_type.addButton(self._rb_item_plan)
        self._grp_item_type.addButton(self._rb_item_instruction)

        self._combo_item_list = ScrollingComboBox()
        self._combo_item_list.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # self._combo_item_list.setSizePolicy(QComboBox.AdjustToContents)
        self._combo_item_list.currentIndexChanged.connect(
            self._combo_item_list_sel_changed
        )

        self._lb_item_source = QLabel(self._current_item_source)

        # Start with 'detailed' view (show optional parameters)
        self._wd_editor = _QtRePlanEditorTable(
            self.model, editable=False, detailed=True
        )
        self._wd_editor.signal_parameters_valid.connect(self._slot_parameters_valid)
        self._wd_editor.signal_item_description_changed.connect(
            self._slot_item_description_changed
        )
        self._wd_editor.signal_cell_modified.connect(self._switch_to_editing_mode)

        self._pb_batch_upload = QPushButton("Batch Upload")
        self._pb_add_to_queue = QPushButton("Add to Queue")
        self._pb_add_to_staging = QPushButton("Add to Staging")
        self._pb_save_item = QPushButton("Save")
        self._pb_reset = QPushButton("Reset")
        self._pb_cancel = QPushButton("Cancel")

        self._pb_batch_upload.clicked.connect(self._pb_batch_upload_clicked)

        self._pb_add_to_queue.clicked.connect(self._pb_add_to_queue_clicked)
        self._pb_add_to_staging.clicked.connect(self._pb_add_to_staging_clicked)
        self._pb_save_item.clicked.connect(self._pb_save_item_clicked)
        self._pb_reset.clicked.connect(self._pb_reset_clicked)
        self._pb_cancel.clicked.connect(self._pb_cancel_clicked)

        self._grp_item_type.buttonToggled.connect(self._grp_item_type_button_toggled)

        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(self._rb_item_scan)
        hbox.addWidget(self._rb_item_plan)
        hbox.addWidget(self._rb_item_all)
        hbox.addWidget(self._rb_item_instruction)
        hbox.addWidget(self._combo_item_list)
        hbox.addStretch(1)
        hbox.addWidget(self._lb_item_source)
        vbox.addLayout(hbox)

        vbox.addWidget(self._wd_editor)

        hbox = QHBoxLayout()
        hbox.addWidget(self._pb_batch_upload)
        hbox.addStretch(1)
        hbox.addWidget(self._pb_add_to_queue)
        hbox.addWidget(self._pb_add_to_staging)
        hbox.addWidget(self._pb_save_item)
        hbox.addWidget(self._pb_reset)
        hbox.addWidget(self._pb_cancel)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.model.events.allowed_plans_changed.connect(self._on_allowed_plans_changed)
        self.signal_allowed_plan_changed.connect(self._slot_allowed_plans_changed)

        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)

        self._set_allowed_item_list()

        self._update_widget_state()

    def _set_allowed_item_list(self):
        # self._queue_item_type must be "plan" or "instruction"
        # self._current_plan_name and self._current_item_name should be properly set.
        #   The first item in the list is selected if the value is set to "".
        #   No element selected if the element with the given name is not in the list.

        def lower(s):
            return s.lower()

        if self._rb_item_plan.isChecked():
            allowed_item_names = self._allowed_plan_list
            allowed_item_names.sort(key=lower)
            if (not self._current_plan_name) and (allowed_item_names):
                self._current_plan_name = allowed_item_names[0]
            item_name = self._current_plan_name

        elif self._rb_item_scan.isChecked():
            allowed_item_names = self._allowed_scan_list
            allowed_item_names.sort(key=lower)
            if (not self._current_plan_name) and (allowed_item_names):
                self._current_plan_name = allowed_item_names[0]
            item_name = self._current_plan_name

        elif self._rb_item_all.isChecked():
            allowed_item_names = self.model.get_allowed_plan_names()
            allowed_item_names.sort(key=lower)
            if (not self._current_plan_name) and (allowed_item_names):
                self._current_plan_name = allowed_item_names[0]
            item_name = self._current_plan_name

        elif self._rb_item_instruction.isChecked():
            allowed_item_names = self.model.get_allowed_instruction_names()
            allowed_item_names.sort(key=lower)
            if (not self._current_instruction_name) and (allowed_item_names):
                self._current_instruction_name = allowed_item_names[0]
            item_name = self._current_instruction_name

        self._combo_item_list.clear()
        self._combo_item_list.addItems(allowed_item_names)

        try:
            index = allowed_item_names.index(item_name)
        except ValueError:
            index = -1

        self._combo_item_list.setCurrentIndex(index)

    def _update_widget_state(self):
        is_connected = bool(self.model.re_manager_connected)

        self._rb_item_plan.setEnabled(not self._edit_mode_enabled)
        self._rb_item_scan.setEnabled(not self._edit_mode_enabled)
        self._rb_item_all.setEnabled(not self._edit_mode_enabled)
        self._rb_item_instruction.setEnabled(not self._edit_mode_enabled)
        self._combo_item_list.setEnabled(not self._edit_mode_enabled)

        self._pb_batch_upload.setEnabled(is_connected)

        self._pb_add_to_queue.setEnabled(self._editor_state_valid and is_connected)
        self._pb_add_to_staging.setEnabled(self._editor_state_valid and is_connected)
        self._pb_save_item.setEnabled(
            self._editor_state_valid
            and is_connected
            and self._current_item_source in ("QUEUE ITEM", "STAGED ITEM")
        )
        self._pb_reset.setEnabled(self._edit_mode_enabled)
        self._pb_cancel.setEnabled(self._edit_mode_enabled)

        self._lb_item_source.setText(self._current_item_source)

    def _update_plan_list(self, plan_list):
        self._allowed_plan_list = plan_list
        self.signal_allowed_plan_changed.emit()

    def _update_scan_list(self, scan_list):
        self._allowed_scan_list = scan_list
        self.signal_allowed_plan_changed.emit()

    def edit_queue_item(self, queue_item):
        """
        Calling this function while another plan is being edited will cancel editing, discard results
        and open another plan for editing.
        """
        self._current_item_source = "QUEUE ITEM"
        self._edit_item(queue_item)

    def edit_staged_item(self, staged_item):
        """
        Calling this function while another plan is being edited will cancel editing, discard results
        and open another plan for editing.
        """
        self._current_item_source = "STAGED ITEM"
        self._edit_item(staged_item)

    def _edit_item(self, queue_item, *, edit_mode=True):
        self._queue_item_name = queue_item.get("name", None)
        self._queue_item_type = queue_item.get("item_type", None)

        if (
            self._queue_item_name
            and self._queue_item_type
            and self._queue_item_type in ("plan", "instruction")
        ):
            # queue item type is handed to QueueServer so it can only be "instruction" or "plan"
            if self._queue_item_type == "instruction":
                self._current_instruction_name = self._queue_item_name
                self._rb_item_instruction.setChecked(True)
            elif self._queue_item_type == "plan":
                self._current_plan_name = self._queue_item_name
                # We are not sure exactly what should be checked, but it shouldn't be instruction
                self._rb_item_instruction.setChecked(False)

            self._ignore_combo_item_list_sel_changed = True
            self._set_allowed_item_list()
            self._ignore_combo_item_list_sel_changed = False

            self._wd_editor.show_item(item=queue_item, editable=True)

            self._edit_mode_enabled = bool(edit_mode)
            self._update_widget_state()

    @Slot()
    def _switch_to_editing_mode(self):
        if not self._edit_mode_enabled:
            self._edit_mode_enabled = True
            self._current_item_source = "NEW ITEM"
            self._update_widget_state()

    def _show_item_preview(self):
        """
        Generate and display preview (not editable)
        """
        item_name = self._combo_item_list.currentText()
        item_type = self._current_item_type
        if item_name:
            item = {"item_type": item_type, "name": item_name}
            self._edit_item(queue_item=item, edit_mode=False)

    def _save_selected_item_name(self):
        item_name = self._combo_item_list.currentText()
        item_type = self._current_item_type
        if item_name:
            if item_type == "plan":
                self._current_plan_name = item_name
            elif item_type == "instruction":
                self._current_instruction_name = item_name

    def on_update_widgets(self, event):
        self.signal_update_widgets.emit()

    @Slot()
    def slot_update_widgets(self):
        self._update_widget_state()

    @Slot(str)
    def _slot_item_description_changed(self, item_description):
        self._combo_item_list.setToolTip(item_description)

    @Slot(bool)
    def _slot_parameters_valid(self, is_valid):
        self._editor_state_valid = is_valid
        self._update_widget_state()

    def _pb_batch_upload_clicked(self):
        dlg = DialogBatchUpload(
            current_dir=self.model.current_dir,
            file_type_list=self.model.plan_spreadsheet_data_types,
            additional_parameters=self.model.plan_spreadsheet_additional_parameters,
        )
        res = dlg.exec()
        if res:
            self.model.current_dir = dlg.current_dir
            file_path = dlg.file_path
            data_type = dlg.file_type
            additional_parameters = dlg.additional_parameters
            try:
                self.model.queue_upload_spreadsheet(
                    file_path=file_path, data_type=data_type, **additional_parameters
                )
            except Exception as ex:
                print(f"Failed to load plans from spreadsheet: {ex}")

    def _pb_add_to_queue_clicked(self):
        """
        Add item to queue
        """
        item = self._wd_editor.get_modified_item()
        try:
            self.model.queue_item_add(item=item)
            self._wd_editor.show_item(item=None)
            self.signal_switch_tab.emit("view")
            self._edit_mode_enabled = False
            self._current_item_source = ""
            self._update_widget_state()
            self._show_item_preview()

        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_add_to_staging_clicked(self):
        """
        Add item to staging queue
        """
        item = self._wd_editor.get_modified_item()
        try:
            self.top_level_model.queue_staging.queue_item_add(item=item)
            self._wd_editor.show_item(item=None)
            self.signal_switch_tab.emit("view")
            self._edit_mode_enabled = False
            self._current_item_source = ""
            self._update_widget_state()
            self._show_item_preview()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_save_item_clicked(self):
        """
        Save item to queue (update the edited item)
        """
        item = self._wd_editor.get_modified_item()
        try:
            if self._current_item_source == "QUEUE ITEM":
                self.model.queue_item_update(item=item)
            elif self._current_item_source == "STAGED ITEM":
                # For staged items, we need to update the staging queue
                # Since we don't have a direct update method, we'll remove and re-add
                # This is a simplified approach - in a real implementation you might
                # want to track the original item's position/UID
                self.top_level_model.queue_staging.queue_item_update(item=item)
            else:
                # Default to main queue
                self.model.queue_item_update(item=item)

            self._wd_editor.show_item(item=None)
            self.signal_switch_tab.emit("view")
            self._edit_mode_enabled = False
            self._current_item_source = ""
            self._update_widget_state()
            self._show_item_preview()
        except Exception as ex:
            print(f"Exception: {ex}")

    def _pb_reset_clicked(self):
        """
        Restore parameters to the original values
        """
        self._wd_editor.reset_item()

    def _pb_cancel_clicked(self):
        self._wd_editor.show_item(item=None)
        self._edit_mode_enabled = False
        self._queue_item_type = ""
        self._queue_item_name = ""
        self._current_item_source = ""
        self._update_widget_state()
        self._show_item_preview()

    def _grp_item_type_button_toggled(self, button, checked):
        if checked:
            if button == self._rb_item_plan:
                self._current_item_type = "plan"
                self._set_allowed_item_list()
            elif button == self._rb_item_all:
                self._current_item_type = "plan"
                self._set_allowed_item_list()
            elif button == self._rb_item_scan:
                self._current_item_type = "plan"
                self._set_allowed_item_list()
            elif button == self._rb_item_instruction:
                self._current_item_type = "instruction"
                self._set_allowed_item_list()

    def _combo_item_list_sel_changed(self, index):
        self._save_selected_item_name()
        # We don't process the case when the list of allowed plans changes and the selected
        #   item is not in the list. But this is not a practical case.
        if not self._ignore_combo_item_list_sel_changed:
            self._show_item_preview()

    def _on_allowed_plans_changed(self, allowed_plans):
        self.signal_allowed_plan_changed.emit()

    @Slot()
    def _slot_allowed_plans_changed(self):
        self._set_allowed_item_list()


class PlanEditor(QWidget):
    signal_update_widgets = Signal()
    signal_running_item_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.run_engine = model.run_engine
        self.user_status = model.user_status

        self._plan_viewer = _QtReViewer(self.model)
        self._plan_editor = _QtReEditor(self.model)

        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._plan_viewer, "Plan Viewer")
        self._tab_widget.addTab(self._plan_editor, "Plan Editor")

        vbox = QVBoxLayout()
        vbox.addWidget(self._tab_widget)
        self.setLayout(vbox)

        self._plan_viewer.signal_edit_queue_item.connect(self.edit_queue_item)
        self._plan_editor.signal_switch_tab.connect(self._switch_tab)

    @Slot(str)
    def _switch_tab(self, tab):
        tabs = {"view": self._plan_viewer, "edit": self._plan_editor}
        self._tab_widget.setCurrentWidget(tabs[tab])

    @Slot(object)
    def edit_queue_item(self, queue_item):
        """
        Calling this function while another plan is being edited will cancel editing, discard results
        and open another plan for editing.
        """
        self._switch_tab("edit")
        self._plan_editor.edit_queue_item(queue_item)
        return True  # Indicates that the plan was accepted

    def edit_staged_item(self, staged_item):
        """
        Calling this function while another plan is being edited will cancel editing, discard results
        and open another plan for editing.
        """
        self._switch_tab("edit")
        self._plan_editor.edit_staged_item(staged_item)
        return True
