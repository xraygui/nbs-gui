from qtpy.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QLineEdit,
    QGroupBox,
    QGridLayout,
    QDialog,
    QListWidget,
    QFrame,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QAbstractScrollArea,
    QTabWidget,
    QScrollArea,
    QTreeView,
    QSizePolicy,
    QFrame,
    QDoubleSpinBox,
    QCheckBox,
)

from bluesky_widgets.qt.threading import *
import ast
from qtpy.QtCore import Qt, Signal, Slot, QEvent
from qtpy.QtGui import (
    QStandardItemModel,
    QStandardItem,
)

from typing import get_origin, get_args
import typing

from bluesky_widgets.qt.run_engine_client import (
    _QtReViewer,
    _QtReEditor,
)

# Global variable for margin
GLOBAL_MARGIN = 2


class QtRePlanEditor(QWidget):
    signal_update_widgets = Signal()
    signal_running_item_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._plan_viewer = _QtReViewer(self.model)
        self._plan_editor = _QtReEditor(self.model)
        self._add_plan = QtCreateNewPlan(self.model)
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._add_plan, "Add Plan")
        self._tab_widget.addTab(self._plan_viewer, "Plan Viewer")
        self._tab_widget.addTab(self._plan_editor, "Plan Editor")

        vbox = QVBoxLayout()
        vbox.addWidget(self._tab_widget)
        self.setLayout(vbox)

        self._plan_viewer.signal_edit_queue_item.connect(self.edit_queue_item)
        self._plan_editor.signal_switch_tab.connect(self._switch_tab)
        # self.model.events.queue_item_edit.connect(self._test_cb)

    @Slot(str)
    def _switch_tab(self, tab):
        tabs = {"view": self._plan_viewer, "edit": self._plan_editor}
        self._tab_widget.setCurrentWidget(tabs[tab])

    @Slot(object)
    def edit_queue_item(self, queue_item):
        self._switch_tab("edit")
        self._plan_editor.edit_queue_item(queue_item)

        # Update checkboxes based on the queue item
        for row in range(self._add_plan.tree_model.rowCount()):
            name_item = self._add_plan.tree_model.item(row, 0)
            send_item = self._add_plan.tree_model.item(row, 1)
            checkbox = self._add_plan.tree.indexWidget(send_item.index())

            name = name_item.text()
            if name in queue_item["kwargs"] or (
                name == "md" and "md" in queue_item["kwargs"]
            ):
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)

    def _test_cb(self, event):
        self._add_plan.signal_edit_item.emit(event)


class QtCreateNewPlan(QTableWidget):
    signal_update_widgets = Signal(bool)
    # signal_switch_tab = Signal(str)
    signal_allowed_plan_changed = Signal(object)
    signal_allowed_devices_changed = Signal(object)
    signal_update_list_of_devices = Signal(object)
    signal_edit_item = Signal(object)

    signal_selection_changed = Signal(object, object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.model.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widgets.connect(self.slot_update_widgets)
        self.signal_selection_changed.connect(self.slot_selection_changed)

        self.model.events.allowed_devices_changed.connect(
            self._on_allowed_devices_changed
        )
        self.signal_allowed_devices_changed.connect(self._slot_allowed_devices_changed)
        self.model.events.allowed_plans_changed.connect(self._on_allowed_plan_changed)
        self.signal_allowed_plan_changed.connect(self._slot_allowed_plan_changed)
        # self.signal_edit_item.connect(self._slot_edit_item)

        self._allowed_devices = {}
        self._allowed_plans = {}

        vbox = QVBoxLayout()
        vbox.setSpacing(GLOBAL_MARGIN)
        vbox.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )

        hbox = QHBoxLayout()
        hbox.setSpacing(GLOBAL_MARGIN)
        self.select_plan = QComboBox(self)
        self.select_plan.setMinimumWidth(100)
        self.select_plan.addItem(None)
        self.select_plan.currentTextChanged.connect(self._select_plan)
        hbox.addWidget(self.select_plan)
        hbox.addStretch()
        self.submit = QPushButton("Submit")
        self.submit.clicked.connect(self.submit_plan)
        hbox.addWidget(self.submit)
        vbox.addLayout(hbox)

        self.input_fields = {}

        self.tree = QTreeView()
        self.tree.setUniformRowHeights(True)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Name", "Send", "Input"])
        self.tree.header().setDefaultSectionSize(120)
        self.tree.setModel(self.tree_model)
        vbox.addWidget(self.tree)

        self.setLayout(vbox)

    def on_update_widgets(self, event):
        # None should be converted to False:
        is_connected = bool(event.is_connected)
        self.signal_update_widgets.emit(is_connected)

    @Slot(object)
    def _slot_edit_item(self, event):
        a = self.select_plan.findText(event.item["name"])
        self.select_plan.setCurrentIndex(a)
        # self._fill_tree(self.tree_model.invisibleRootItem(), self._allowed_plans[event.item['name']])
        for arg, val in event.item["kwargs"].items():
            if arg == "md":
                self.input_fields[arg].set_value(str(val["md"]))
            else:
                self.input_fields[arg].set_value(val)

    @Slot()
    def slot_update_widgets(self):
        self._update_widget_state()

    def _update_widget_state(self):

        is_connected = bool(self.model.re_manager_connected)

        # self._rb_item_plan.setEnabled(not self._edit_mode_enabled)
        # self._rb_item_instruction.setEnabled(not self._edit_mode_enabled)
        self.select_plan.setEnabled(is_connected)

        # self._pb_add_to_queue.setEnabled(is_connected)

    def _on_allowed_devices_changed(self, event):
        self.signal_allowed_devices_changed.emit(event.allowed_devices)

    @Slot(object)
    def _slot_allowed_devices_changed(self, allowed_devices):
        self._allowed_devices = allowed_devices
        self.signal_update_list_of_devices.emit(allowed_devices)

    def _on_allowed_plan_changed(self, event):
        self.signal_allowed_plan_changed.emit(event.allowed_plans)

    @Slot(object)
    def _slot_allowed_plan_changed(self, allowed_plans):
        self._allowed_plans = allowed_plans
        self.select_plan.clear()
        self.select_plan.addItem(None)
        sorted_plans = sorted(allowed_plans.keys())  # Sort the plan names
        self.select_plan.addItems(sorted_plans)

    @Slot(object, object)
    def slot_selection_changed(self, source, selection):
        for name, field in self.input_fields.items():
            try:
                is_dependant = field.depends_on == source
            except AttributeError as e:
                is_dependant = False
            if is_dependant:
                if selection == "":
                    field.set_field([])
                elif isinstance(selection, list):
                    print("List dependency not yet implemented!")
                else:
                    items = [i for i in field.selection_dict[selection]]
                    field.set_field(items)

    def submit_plan(self):
        item = {
            "item_type": "plan",
            "name": str(self.select_plan.currentText()),
            "args": {},
            "kwargs": {},
        }

        for row in range(self.tree_model.rowCount()):
            name_item = self.tree_model.item(row, 0)
            send_item = self.tree_model.item(row, 1)
            checkbox = self.tree.indexWidget(send_item.index())

            if checkbox.isChecked():
                name = name_item.text()
                if name != "md":
                    value = self.input_fields[name].get_value()
                    if value is not None:  # Only include non-None values
                        item["kwargs"][name] = value
                else:
                    md_value = self.input_fields[name].get_value()
                    if md_value:  # Only include non-empty md
                        item["kwargs"]["md"] = {"md": md_value}

        try:
            self.model.queue_item_add(item=item)
        except RuntimeError as e:
            print(e)

    def _select_plan(self, text):
        # remove current widgets
        self.tree_model.clear()
        self.input_fields = {}
        self.tree_model.setHorizontalHeaderLabels(["Name", "Send", "Input"])
        if not text:
            return
        self._fill_tree(self.tree_model.invisibleRootItem(), self._allowed_plans[text])

    def _fill_tree(self, root, plan):
        for param in plan["parameters"]:
            name_item = QStandardItem(param["name"])
            name_item.setEditable(False)

            send_item = QStandardItem()
            send_item.setEditable(False)
            checkbox = QCheckBox()

            is_required = (
                param.get("kind").get("name")
                in ["POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY"]
                and param.get("default", None) is None
            )

            checkbox.setChecked(is_required)
            checkbox.setEnabled(not is_required)  # Disable checkbox if required

            input_item = QStandardItem()
            input_widget = self._create_input(param)
            self.input_fields[param["name"]] = input_widget

            root.appendRow([name_item, send_item, input_item])
            self.tree.setIndexWidget(send_item.index(), checkbox)
            self.tree.setIndexWidget(input_item.index(), input_widget)

            # Adjust the size of the input widget
            input_widget.setMaximumHeight(25)  # Reduce the height of input widgets

    def _create_input(self, param):
        _name = param["name"]
        default = param.get("default", None)
        print(param)
        if "annotation" not in param:
            annotation = {}
            if default is not None:
                try:
                    default_value = ast.literal_eval(default)
                    _type = type(default_value).__name__
                    if _type == "int":
                        _type = "float"  # We can't be too specific from a default value
                except (ValueError, SyntaxError):
                    _type = "str"
            else:
                _type = "str"
        else:
            annotation = param["annotation"]
            if isinstance(annotation, dict):
                _type = annotation.get("type", "str")
            else:
                _type = str(annotation)

        # Handle Optional types
        if _type.startswith("typing.Optional") or _type.startswith("typing.Union"):
            try:
                args = get_args(eval(_type))
            except:
                args = []
            if type(None) in args:
                # It's an Optional type
                non_none_types = [arg for arg in args if arg is not type(None)]
                if len(non_none_types) == 1:
                    _type = non_none_types[0].__name__
                else:
                    _type = "typing.Union"
            else:
                _type = "typing.Union"

        # Handle specific types
        if _type == "typing.List" or _type == "typing.Sequence":
            return QtDeviceInput(
                name=_name,
                items=self._allowed_devices,
            )

        elif _type == "typing.Union":
            depends_on = param.get("description", "")
            if "enums" in annotation:
                selection_dict = annotation["enums"]
            else:
                selection_dict = annotation.get("devices", {})

            _numeric_dict = {
                "min": None,
                "max": None,
                "default": default,
                "step": None,
            }

            for key in _numeric_dict:
                if key in param:
                    try:
                        _numeric_dict[key] = float(param[key])
                    except ValueError:
                        _numeric_dict[key] = None

            device = QtUnionInput(
                name=_name,
                selection_dict=selection_dict,
                depends_on=depends_on,
                numeric_dict=_numeric_dict,
            )

            def callback(name, selection):
                self.signal_selection_changed.emit(name, selection)

            device.add_callback(callback)

            return device

        elif "enums" in annotation:
            _name = next(iter(annotation["enums"]))
            device = QtEnumInput(
                name=_name,
                items=annotation["enums"][_name],
            )

            def callback(name, selection):
                self.signal_selection_changed.emit(name, selection)

            device.add_callback(callback)

            return device

        elif _type in ("int", "float"):
            is_int = _type == "int"
            _numeric_dict = {
                "min": None,
                "max": None,
                "default": default,
                "step": None,
            }

            for key in _numeric_dict:
                if key in param:
                    try:
                        _numeric_dict[key] = float(param[key])
                    except ValueError:
                        _numeric_dict[key] = None

            return QtNumericInput(
                name=_name,
                is_int=is_int,
                **_numeric_dict,
            )
        elif _type == "bool":
            return QtBoolInput(name=_name)
        else:
            return QtTextInput(name=_name)


class QtTextInput(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )
        hbox.setSpacing(GLOBAL_MARGIN)
        self.name = name
        self.field = QLineEdit()
        hbox.addWidget(self.field)
        self.setLayout(hbox)

    def get_value(self):
        return self.field.text()

    def set_value(self, value):
        self.field.setText(value)


class QtBoolInput(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )
        hbox.setSpacing(GLOBAL_MARGIN)
        self.name = name
        self.field = QCheckBox()
        hbox.addWidget(self.field)
        self.setLayout(hbox)

    def get_value(self):
        return self.field.isChecked()

    def set_value(self, value):
        self.field.setChecked(value)


class QtNumericInput(QWidget):
    def __init__(self, name, is_int, default, min, max, step, parent=None):
        super().__init__(parent)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )
        hbox.setSpacing(GLOBAL_MARGIN)
        self.name = name
        self.is_int = is_int
        self.field = QDoubleSpinBox()
        if is_int:
            self.field.setDecimals(0)
        else:
            self.field.setDecimals(2)

        if not default is None:
            self.field.setValue(default)
        else:
            self.field.clear()
        if not step is None:
            self.field.setSingleStep(step)
        if not min is None:
            self.field.setMinimum(min)
        if not max is None:
            self.field.setMaximum(max)

        hbox.addWidget(self.field)
        self.setLayout(hbox)

    def get_value(self):
        try:
            if self.is_int:
                return int(self.field.value())
            else:
                return float(self.field.value())
        except ValueError as e:
            return 0

    def set_value(self, val):
        self.field.setValue(val)


class QtUnionInput(QWidget):
    def __init__(
        self, name, numeric_dict, depends_on=None, selection_dict={}, parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.selection_dict = selection_dict
        self.depends_on = depends_on
        self.numeric_dict = numeric_dict
        self.callbacks = []
        self.box = QHBoxLayout()
        self.field = QtTextInput(name=self.name)
        self.field.setEnabled(False)
        self.box.addWidget(self.field)
        self.box.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )
        self.setLayout(self.box)

    def add_callback(self, callback):
        self.callbacks.append(callback)

    def selection_changed(self, name, selection):
        for callback in self.callbacks:
            callback(name, selection)

    def set_field(self, selection):
        self.setEnabled(True)
        if self.box.count() > 0:
            self.box.removeWidget(self.field)
        if len(selection) == 0:
            self.field = QtTextInput(name=self.name)
            self.box.addWidget(self.field)
            self.setEnabled(False)
        else:
            if "widget:" in selection[0]:
                _type = selection[0].split(":")[1]
                if _type == "float" or _type == "int":
                    self.field = QtNumericInput(
                        name=self.name, is_int=False, **self.numeric_dict
                    )
                    self.box.addWidget(self.field)
                elif _type == "None":
                    self.setEnabled(False)
                    self.field = QtTextInput(name=self.name)
                    self.box.addWidget(self.field)
                else:
                    print(_type)
            else:
                self.field = QtEnumInput(
                    name=self.name,
                    items=selection,
                )
                self.field.add_callback(self.selection_changed)
                self.box.addWidget(self.field)

    def get_value(self):
        val = self.field.get_value()
        if val == "":
            return None
        else:
            return val

    def set_value(self, val):
        self.field.set_value(val)


class QtEnumInput(QWidget):
    def __init__(self, name, items, parent=None):
        super().__init__(parent)
        self.name = name
        self.items = items
        self.callbacks = []
        hbox = QHBoxLayout()
        hbox.setContentsMargins(
            GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN, GLOBAL_MARGIN
        )
        hbox.setSpacing(GLOBAL_MARGIN)
        self.field = QComboBox()
        if len(items) > 1:
            self.field.addItem("")
        self.field.addItems(items)
        self.field.currentTextChanged.connect(self.selection_changed)
        hbox.addWidget(self.field)
        self.setLayout(hbox)

    def set_items(self, devices):
        self.items = devices
        self.field.clear()
        self.field.addItem("")
        self.field.addItems(devices)

    def add_callback(self, callback):
        self.callbacks.append(callback)
        callback(self.name, self.field.currentText())

    def selection_changed(self, selection):
        for callback in self.callbacks:
            callback(self.name, selection)

    def get_value(self):
        return str(self.field.currentText())

    def set_value(self, val):
        print("TODO")


class QtDeviceInput(QWidget):
    def __init__(self, name, items, depends_on="", selection_dict={}, parent=None):
        super().__init__(parent)
        self.depends_on = depends_on
        self.name = name
        self.filter = []
        self.callbacks = []
        self.items = items
        self.selection_dict = selection_dict
        self.add_device_btn = QComboBox()
        self.add_device_label = "Add " + self.name
        self.add_device_btn.currentTextChanged.connect(self.add_device)
        self.device_list = QtDeviceList()
        self.device_list.signal_device_list_changed.connect(self.device_list_changed)
        vbox = QVBoxLayout()
        vbox.addWidget(self.add_device_btn)
        vbox.addWidget(self.device_list)
        self.setLayout(vbox)

        self.set_items(items)

    def get_selected_devices(self):
        return self.device_list.devices

    def add_callback(self, callback):
        self.callbacks.append(callback)
        callback(self.device_list.items)

    def device_list_changed(self):
        items = [i for i in self.items if i not in self.device_list.devices]
        self.add_device_btn.clear()
        self.add_device_btn.addItem(self.add_device_label)
        self.add_device_btn.addItems(items)

    def add_device(self, selection):
        if not selection == self.add_device_label and not selection == "":
            self.add_device_btn.setCurrentIndex(0)
            self.device_list.add_device(selection)
            for callback in self.callbacks:
                callback(self.device_list.devices)

    def set_items(self, devices):
        self.items = devices
        self.add_device_btn.clear()
        self.device_list.clear()
        self.add_device_btn.addItem(self.add_device_label)
        self.add_device_btn.addItems(devices)

    def get_value(self):
        return self.device_list.devices

    def set_value(self, val):
        print("TODO")


class QtDeviceList(QTableWidget):

    signal_device_list_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setRowCount(0)
        self.devices = []
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.itemDoubleClicked.connect(self.remove_device)

    def add_device(self, text):
        pos = len(self.devices)
        self.setRowCount(pos + 1)
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        self.setItem(pos, 0, item)
        self.devices.append(text)
        self.resizeRowsToContents()
        self.signal_device_list_changed.emit()

    def remove_device(self, item):
        device = item.text()
        self.devices.remove(device)
        for row in range(self.rowCount()):
            if self.item(row, 0).text() == device:
                self.removeRow(row)
                break
        self.setRowCount(len(self.devices))
        self.signal_device_list_changed.emit()

    def clear(self):
        self.setRowCount(0)
        self.devices = []
