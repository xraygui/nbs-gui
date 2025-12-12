from qtpy.QtWidgets import (
    QWidget,
    QComboBox,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QTextEdit,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Signal
from typing import Any
from collections import defaultdict
from ..widgets.qt_custom import ScrollingComboBox


class BaseParam(QWidget):
    editingFinished = Signal()

    def __init__(self, key, label, help_text="", parent=None):
        # print(f"Setting up BaseParam with {key}, {label}, {help_text}, {parent}")
        super().__init__(parent=parent)
        self.key = key
        self.label_text = label
        if help_text == "":
            self.help_text = label
        else:
            self.help_text = help_text
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Set the tooltip to display help_text
        self.setToolTip(self.help_text)
        # print("Done setting up BaseParam")

    def reset(self):
        raise NotImplementedError

    def get_params(self):
        raise NotImplementedError

    def check_ready(self):
        return True


class LineEditParam(BaseParam):
    def __init__(self, key, value_type, label, help_text="", parent=None):
        super().__init__(key, label, help_text, parent)
        self.input_widget = QLineEdit()
        self.layout.addWidget(self.input_widget)
        self.input_widget.editingFinished.connect(self.editingFinished.emit)
        if value_type == int:
            self.input_widget.setValidator(QIntValidator())
            self.label_text = label + " (int)"

        elif value_type == float:
            self.input_widget.setValidator(QDoubleValidator())
            self.label_text = label + " (float)"
        else:
            self.label_text = label + " (text)"

        self.value_type = value_type

    def reset(self):
        self.input_widget.setText("")

    def get_params(self):
        value = self.input_widget.text()
        if value == "":
            return {}
        if self.value_type in (int, float):
            value = self.value_type(value)
        return {self.key: value}

    def check_ready(self):
        """
        Check if the widget has a valid value.

        Returns
        -------
        bool
            True if the input widget has a non-empty value, False otherwise.
        """
        value = self.input_widget.text()
        return bool(value and value.strip())


class TextEditParam(BaseParam):
    def __init__(self, key, label, help_text="", parent=None):
        super().__init__(key, label, help_text, parent)
        self.input_widget = QTextEdit(self)
        self.layout.addWidget(self.input_widget)
        self.input_widget.textChanged.connect(self.editingFinished.emit)

    def reset(self):
        """
        Reset the text edit to an empty state.
        """
        self.input_widget.clear()

    def get_params(self):
        """
        Get the current parameter value.

        Returns
        -------
        dict
            A dictionary containing the current text of the text edit.
        """
        text = self.input_widget.toPlainText()
        return {self.key: text} if text else {}

    def check_ready(self):
        """
        Check if the widget is ready for use.

        Returns
        -------
        bool
            True if the text edit contains any text, False otherwise.
        """
        return bool(self.input_widget.toPlainText().strip())


class ComboBoxParam(BaseParam):
    def __init__(self, key, options, label, help_text="", parent=None, default=None):
        print(
            f"Setting up ComboBoxParam with {key}, {options}, {label}, {help_text}, {parent}, {default}"
        )
        super().__init__(key, label, help_text, parent)
        # print(f"Done setting up ComboBoxParam super init {self.label_text}")
        self.input_widget = ScrollingComboBox(max_visible_items=10)
        # print("Adding widget to layout")
        self.layout.addWidget(self.input_widget)
        # print("Done adding widget to layout")
        self.default = default
        # print(f"Before update_options for ComboBoxParam {self.label_text} to {options}")
        self._update_options(options)
        # print(f"Done updating options for ComboBoxParam {self.label_text}")

    def _update_options(self, options):
        # Store original values and their string representations
        # print(f"Updating options for ComboBoxParam {self.label_text} to {options}")
        self.options = options

        if isinstance(options, dict):
            self.options_map = options
        elif isinstance(options, (list, tuple)):
            self.options_map = {str(val): val for val in options}
        elif options is None:
            self.options_map = {}
        else:
            raise ValueError(
                f"Unsupported options type for ComboBoxParam {self.label_text}: {type(options)}"
            )
        # Add string representations to combo box
        self.input_widget.addItems([opt for opt in self.options_map.keys()])
        self.input_widget.currentIndexChanged.connect(
            lambda x: self.editingFinished.emit()
        )

        if self.default is not None and self.default in options:
            self.input_widget.setCurrentText(str(self.default))
        else:
            self.input_widget.setCurrentIndex(-1)

    def reset(self):
        self.input_widget.setCurrentIndex(-1)

    def get_params(self):
        current_text = self.input_widget.currentText()
        if not current_text:
            return {}
        # Return the original value type using our mapping
        return {self.key: self.options_map[current_text]}


class BooleanParam(ComboBoxParam):
    def __init__(self, key, label, help_text="", parent=None, default=None):
        default_str = str(default) if default is not None else None
        super().__init__(
            key, ["True", "False"], label, help_text, parent, default=default_str
        )

    def get_params(self):
        return {self.key: self.input_widget.currentText() == "True"}


class SpinBoxParam(BaseParam):
    def __init__(
        self,
        key,
        label,
        help_text="",
        parent=None,
        value_type=int,
        minimum=None,
        maximum=None,
        decimals=2,
        default=None,
    ):
        # print("Going to initialize baseParam")
        super().__init__(key, label, help_text, parent)
        self.value_type = value_type
        self.default = default
        self.no_default = default is None
        # print("Determining what kind of spinbox to make")
        if value_type == int:
            self.input_widget = QSpinBox(self)
        elif value_type == float:
            self.input_widget = QDoubleSpinBox(self)
            self.input_widget.setDecimals(decimals)
        else:
            raise ValueError("value_type must be int or float")

        self.layout.addWidget(self.input_widget)

        if minimum is not None:
            self.input_widget.setMinimum(minimum)
        if maximum is not None:
            self.input_widget.setMaximum(maximum)
        else:
            self.input_widget.setMaximum(1000)

        if self.no_default:
            new_min = self.input_widget.minimum() - self.input_widget.singleStep()
            self.input_widget.setMinimum(new_min)
            self.input_widget.setSpecialValueText(" ")
            self.input_widget.setValue(new_min)
        elif default is not None:
            self.input_widget.setValue(default)

        self.input_widget.valueChanged.connect(lambda x: self.editingFinished.emit())

    def reset(self):
        """
        Reset the spinbox to its initial state.
        """
        if self.no_default:
            self.input_widget.setValue(self.input_widget.minimum())
        else:
            self.input_widget.setValue(self.default)

    def get_params(self):
        """
        Get the current parameter value.

        Returns
        -------
        dict
            A dictionary containing the current value of the spinbox, or an empty dict if unset.
        """
        if self.no_default and self.input_widget.value() == self.input_widget.minimum():
            return {}
        return {self.key: self.input_widget.value()}

    def check_ready(self):
        """
        Check if the widget is ready for use.

        Returns
        -------
        bool
            True if the spinbox has a valid value (not unset), False otherwise.
        """
        if self.no_default:
            return self.input_widget.value() > self.input_widget.minimum()
        return True


def AutoParam(key, value, label, help_text="", parent=None):
    if value in (int, float, str):
        return LineEditParam(key, value, label, help_text, parent)
    elif isinstance(value, list):
        return ComboBoxParam(key, value, label, help_text, parent)
    elif value is bool:
        return BooleanParam(key, label, help_text, parent)


class DynamicComboParam(ComboBoxParam):
    signal_update_options = Signal(object)

    def __init__(
        self, key, label, dummy_text="Select an option", help_text="", parent=None
    ):
        # print(
        #     f"Setting up DynamicComboParam with {key}, {label}, {help_text}, {parent}"
        # )
        self.dummy_text = dummy_text
        super().__init__(key, [], label, help_text, parent)
        self.reset()
        self.signal_update_options.connect(self.update_options)
        # print("Done setting up DynamicComboParam")

    def reset(self):
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)

    def update_options(self, options):
        # print("Updating options for DynamicComboParam")

        if self.input_widget.count() > 0:
            current_text = self.input_widget.currentText()
            self.default = current_text
        else:
            self.default = None
        self.reset()
        self._update_options(options)

    def get_params(self):
        return {} if self.input_widget.currentIndex() == 0 else super().get_params()

    def check_ready(self):
        return self.input_widget.currentIndex() != 0


class MotorParam(DynamicComboParam):
    def __init__(self, key, label, user_status, parent=None):
        super().__init__(key, label, dummy_text="Select a group", parent=parent)
        self.user_status = user_status

        self.motors = {}
        self.groups = defaultdict(list)

        # Main group selector
        self.input_widget.currentTextChanged.connect(self.update_submotor_list)

        # Sub-motor selector
        self.submotor_combo = QComboBox()
        self.submotor_combo.setEnabled(False)

        self.layout.addWidget(self.submotor_combo)
        self.user_status.register_signal(
            "MOTORS_DESCRIPTIONS", self.signal_update_options
        )

    def _group_motors(self, motor_dict):
        """Group motors based on prefix before underscore."""
        groups = defaultdict(list)
        standalone = []

        for display_name, motor_name in motor_dict.items():
            if "." in motor_name:
                prefix, suffix = motor_name.split(".", 1)
                groups[prefix].append((display_name, motor_name))
            else:
                standalone.append((display_name, motor_name))

        # Add standalone motors as their own "group"
        for display_name, motor_name in standalone:
            groups[motor_name] = [(display_name, motor_name)]

        return groups

    def update_options(self, plan_dict):
        """Update the available motor options and organize them hierarchically."""
        # Create inverted dictionary (display name -> motor name)
        print("Updating motor options")
        inverted_dict = {}
        for key, value in plan_dict.items():
            if value != "":
                inverted_dict[value] = key
            else:
                inverted_dict[key] = key

        self.motors = inverted_dict
        self.groups = self._group_motors(inverted_dict)

        # Update group combo box
        self.input_widget.clear()
        self.input_widget.addItem("Select a motor")
        self.input_widget.addItems(sorted(self.groups.keys()))

    def update_submotor_list(self, group_name):
        """Update the submotor combo box based on selected group."""
        self.submotor_combo.clear()
        print(f"Updating submotor list for group: {group_name}")
        if group_name and group_name != "Select a motor":
            motors = self.groups.get(group_name, [])
            print(f"Motors in group: {motors}")
            if len(motors) > 1:
                # Multiple motors in group - enable submotor selection
                self.submotor_combo.setEnabled(True)
                self.submotor_combo.addItem("Select a component")
                for display_name, _ in sorted(motors):
                    self.submotor_combo.addItem(display_name)
            else:
                # Single motor - disable submotor selection
                self.submotor_combo.setEnabled(False)

    def get_params(self):
        """Get the selected motor parameter."""
        group = self.input_widget.currentText()
        if group == "Select a motor":
            return {}

        motors = self.groups.get(group, [])
        if len(motors) == 1:
            # Return the single motor in this group
            return {self.key: motors[0][1]}
        else:
            # Get selection from submotor combo
            selected = self.submotor_combo.currentText()
            if selected and selected != "Select a component":
                for display_name, motor_name in motors:
                    if display_name == selected:
                        return {self.key: motor_name}
        return {}


class ParamGroupBase:
    editingFinished = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = []

    def add_param(self, param, position=None):
        """
        Add a parameter to the group.

        Parameters
        ----------
        param : BaseParam
            The parameter to add to the group.
        position : int, optional
            The position to insert the parameter. If None, append to the end.
        """

        self.params.append(param)
        param.editingFinished.connect(self.editingFinished)

    def reset(self):
        """
        Reset all input fields to their default values.
        """
        for param in self.params:
            param.reset()

    def get_params(self):
        """
        Get parameters from the input widgets.

        Returns
        -------
        dict
            A dictionary of parameters.
        """
        params = {}
        for param in self.params:
            params.update(param.get_params())
        return params

    def check_ready(self):
        """
        Check if the widget is ready for use.

        Returns
        -------
        bool
            True if all required fields are filled, False otherwise.
        """
        return all(param.check_ready() for param in self.params)


class ParamGroup(ParamGroupBase, QGroupBox):
    def __init__(self, parent=None, title=""):
        # print("Setting up ParamGroup")
        super().__init__(title, parent)
        self.layout = QFormLayout(self)
        self.layout.setSpacing(2)  # Reduced from 5
        self.layout.setContentsMargins(2, 2, 2, 2)  # Reduced from 5,5,5,5
        # print("Done setting up ParamGroup")

    def add_param(self, param, position=None):
        """
        Add a parameter to the group.

        Parameters
        ----------
        param : BaseParam
            The parameter to add to the group.
        position : int, optional
            The position to insert the parameter. If None, append to the end.
        """
        super().add_param(param, position)
        label = QLabel(param.label_text)
        self.add_row(label, param, position)

    def add_row(self, label, widget, position=None):
        if position is None:
            self.layout.addRow(label, widget)
        else:
            self.layout.insertRow(position, label, widget)


class AutoParamGroup(ParamGroup):
    def __init__(self, model, parent=None, title="", **kwargs):
        # print("Setting up AutoParamGroup")
        super().__init__(parent=parent, title=title)
        self.model = model
        self.setup_params(**kwargs)
        # print("Done Setting up AutoParamGroup")

    def setup_params(self, **kwargs):
        # print("Setup Params")
        for key, value in kwargs.items():
            if isinstance(value, (list, tuple)):
                label_str = value[0]
                param_info = value[1]
            elif isinstance(value, dict):
                label_str = value.pop("label", key)
                param_info = value
            else:
                label_str = key
                param_info = value
            # print(f"Making AutoParam for {key}:{label_str}")
            self.add_auto_param(key, param_info, label_str)
            # print(f"Added AutoParam for {key}:{label_str}")

    def add_auto_param(self, key: str, value: Any, label: str):
        input_widget = self.auto_param(key, value, label)
        self.add_param(input_widget)

    def auto_param(self, key: str, value: Any, label: str) -> BaseParam:
        if isinstance(value, dict):
            param_type = value.get("type", "default")
            param_args = value.get("args", {})
            help_text = value.get("help_text", "")

            if param_type == "motor":
                return MotorParam(key, label, self.model.user_status, **param_args)
            elif param_type == "spinbox":
                # print(
                #     f"SpinBoxParam arguments: key={key}, label={label}, **{param_args}"
                # )
                return SpinBoxParam(key, label, help_text=help_text, **param_args)
            elif param_type == "combo":
                return ComboBoxParam(
                    key,
                    value.get("options", []),
                    label,
                    help_text=help_text,
                    default=value.get("default", None),
                )
            elif param_type in ["boolean", bool]:
                return BooleanParam(
                    key,
                    label,
                    help_text=help_text,
                    default=value.get("default", None),
                )
            elif param_type == "text":
                return TextEditParam(key, label, help_text=help_text)
            elif param_type == "multiline_text":
                return TextEditParam(key, label, help_text=help_text)
            else:
                return LineEditParam(key, param_type, label, help_text=help_text)
        elif value in (int, float, str):
            return LineEditParam(key, value, label)
        elif isinstance(value, list):
            return ComboBoxParam(key, value, label)
        elif value is bool:
            return BooleanParam(key, label)
        else:
            raise ValueError(f"Unsupported parameter type for key '{key}'")
