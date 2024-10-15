from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Signal, Qt


class BaseParam(QWidget):
    editingFinished = Signal()

    def __init__(self, parent=None):
        print("In BaseParam")
        super().__init__(parent)
        print("Setting Layout")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def reset(self):
        raise NotImplementedError

    def get_params(self):
        raise NotImplementedError

    def check_ready(self):
        return True


class LineEditParam(BaseParam):
    def __init__(self, key, value_type, label, parent=None):
        super().__init__(parent)
        self.key = key
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


class ComboBoxParam(BaseParam):
    def __init__(self, key, options, label, parent=None):
        super().__init__(parent)
        self.key = key
        self.label_text = label
        self.input_widget = QComboBox()
        self.layout.addWidget(self.input_widget)
        self.input_widget.addItem("none")
        self.input_widget.addItems(options)
        self.input_widget.currentIndexChanged.connect(self.editingFinished.emit)

    def reset(self):
        self.input_widget.setCurrentIndex(-1)

    def get_params(self):
        return {self.key: self.input_widget.currentText()}


class BooleanParam(ComboBoxParam):
    def __init__(self, key, label, parent=None):
        super().__init__(key, ["True", "False"], label, parent)

    def get_params(self):
        return {self.key: self.input_widget.currentText() == "True"}


class SpinBoxParam(BaseParam):
    def __init__(self, key, label, parent=None, minimum=None, maximum=None):
        super().__init__(parent)
        self.key = key
        self.label_text = label
        self.input_widget = QSpinBox()
        self.layout.addWidget(self.input_widget)

        if minimum is not None:
            self.input_widget.setMinimum(minimum)
        if maximum is not None:
            self.input_widget.setMaximum(maximum)
        self.input_widget.valueChanged.connect(self.editingFinished.emit)

    def reset(self):
        if self.input_widget.minimum() is not None:
            self.input_widget.setValue(self.input_widget.minimum())
        else:
            self.input_widget.setValue(0)

    def get_params(self):
        """
        Get the current parameter value.

        Returns
        -------
        dict
            A dictionary containing the current value of the spinbox.
        """
        return {self.key: self.input_widget.value()}

    def check_ready(self):
        """
        Check if the widget is ready for use.

        Returns
        -------
        bool
            True if the spinbox value is greater than its minimum, False otherwise.
        """
        return self.input_widget.value() > self.input_widget.minimum()


def AutoParam(key, value, label, parent=None):
    if value in (int, float, str):
        return LineEditParam(key, value, label, parent)
    elif isinstance(value, list):
        return ComboBoxParam(key, value, label, parent)
    elif value is bool:
        return BooleanParam(key, label, parent)


class DynamicComboParam(ComboBoxParam):
    signal_update_options = Signal(object)

    def __init__(self, key, label, dummy_text="Select an option", parent=None):
        super().__init__(key, [], label, parent)
        self.dummy_text = dummy_text
        self.reset()
        self.signal_update_options.connect(self.update_options)

    def reset(self):
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)

    def update_options(self, options):
        current_text = self.input_widget.currentText()
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)

        if isinstance(options, dict):
            for key, value in options.items():
                self.input_widget.addItem(str(key), value)
        elif isinstance(options, list):
            self.input_widget.addItems(options)

        index = self.input_widget.findText(current_text)
        self.input_widget.setCurrentIndex(index if index >= 0 else 0)

    def get_params(self):
        return {} if self.input_widget.currentIndex() == 0 else super().get_params()

    def check_ready(self):
        return self.input_widget.currentIndex() != 0


class ParamGroup(QGroupBox):
    editingFinished = Signal()

    def __init__(self, parent=None, title=""):
        super().__init__(title, parent)
        self.layout = QFormLayout(self)
        self.layout.setSpacing(5)  # Adjust spacing as needed
        self.layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        self.params = []

    def add_param(self, param):
        """
        Add a parameter to the group.

        Parameters
        ----------
        param : BaseParam
            The parameter to add to the group.
        """
        # print("Adding param")
        param.setStyleSheet("QWidget { background-color: red; }")
        self.params.append(param)
        label = QLabel(param.label_text)
        self.layout.addRow(label, param)
        param.editingFinished.connect(self.editingFinished)

    def reset(self):
        for param in self.params:
            param.reset()

    def get_params(self):
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


class AutoParamGroup(ParamGroup):
    def __init__(self, parent=None, title="", **kwargs):
        print("Setting up AutoParamGroup")
        super().__init__(parent=parent, title=title)
        for key, value in kwargs.items():
            if isinstance(value, (list, tuple)):
                labelStr = value[0]
                value = value[1]
            else:
                labelStr = key
            print(f"Making AutoParam for {key}:{labelStr}")
            input_widget = AutoParam(key, value, labelStr)
            self.add_param(input_widget)
            print(f"Added AutoParam for {key}:{labelStr}")
        print("Done Setting up AutoParamGroup")


class PlanWidgetBase(QWidget):
    widget_updated = Signal()
    plan_ready = Signal(bool)

    def __init__(self, model, parent=None, plans="", **kwargs):
        """
        If plan is a string, it will be used as the item name for submission
        If it is a dict, it will be used to create a drop-down menu
        """
        super().__init__(parent)
        self.model = model
        self.plans = plans
        if isinstance(plans, str):
            self.current_plan = plans

        self.run_engine_client = model.run_engine
        self.user_status = model.user_status
        self.layout = QVBoxLayout(self)
        self.basePlanLayout = QVBoxLayout()
        self.layout.addLayout(self.basePlanLayout)

        self.params = []
        self.setup_widget()

    def current_plan_changed(self, idx):
        plan_display = self.plan_combo_list.currentText()
        self.current_plan = self.plans[plan_display]

    def setup_widget(self):
        print("PlanWidgetBase setup_widget")
        if isinstance(self.plans, dict):
            self.plan_combo_list = QComboBox()
            for display_key in self.plans.keys():
                self.plan_combo_list.addItem(display_key)
            self.plan_combo_list.currentIndexChanged.connect(self.current_plan_changed)
            h = QHBoxLayout()
            h.addWidget(QLabel("Plan Subtype"))
            h.addWidget(self.plan_combo_list)
            self.basePlanLayout.addLayout(h)
        print("PlanWidgetBase setup_widget finished")

    def get_params(self):
        """
        Get parameters from the input widgets.

        Returns
        -------
        dict
            A dictionary of parameters.
        """
        params = {}
        for widget in self.params:
            params.update(widget.get_params())
        return params

    def check_plan_ready(self):
        checks = [widget.check_ready() for widget in self.params]
        if all(checks):
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def reset(self):
        for widget in self.params:
            widget.reset()


class BasicPlanWidget(PlanWidgetBase):
    def __init__(self, model, parent=None, plans="", **kwargs):
        """
        If plan is a string, it will be used as the item name for submission
        If it is a dict, it will be used to create a drop-down menu
        """
        self.initial_kwargs = kwargs
        super().__init__(model, parent, plans)

    def setup_widget(self):
        print("BasicPlanWidget setup_widget")
        super().setup_widget()
        self.planWidget = AutoParamGroup(self, **self.initial_kwargs)
        print("Updating input widgets")
        self.params.append(self.planWidget)
        print("Adding widget to layout")
        self.layout.addWidget(self.planWidget)
        print("BasicPlanWidget setup_widget finished")
