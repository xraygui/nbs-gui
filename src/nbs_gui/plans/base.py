from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QHBoxLayout,
    QLabel,
)
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtCore import Signal


class BaseParam(QWidget):
    editingFinished = Signal()

    def reset(self):
        raise NotImplementedError

    def get_params(self):
        raise NotImplementedError

    def check_ready(self):
        print("Checking Ready")
        return True


class LineEditParam(BaseParam):
    def __init__(self, key, value, label, parent=None):
        super().__init__(parent=parent)
        self.key = key
        self.layout = QHBoxLayout(self)
        self.input_widget = QLineEdit()
        self.input_widget.editingFinished.connect(self.editingFinished.emit)
        if value == int:
            self.input_widget.setValidator(QIntValidator())
            label = label + " (int)"
        elif value == float:
            self.input_widget.setValidator(QDoubleValidator())
            label = label + " (float)"
        else:
            label = label + " (text)"
        self.layout.addWidget(QLabel(label))
        self.layout.addWidget(self.input_widget)

    def reset(self):
        self.input_widget.setText("")

    def get_params(self):
        value = self.input_widget.text()
        if value == "":
            return {}
        if isinstance(self.input_widget.validator(), QIntValidator):
            value = int(value)
        elif isinstance(self.input_widget.validator(), QDoubleValidator):
            value = float(value)
        return {self.key: value}


class ComboBoxParam(BaseParam):
    def __init__(self, key, value, label, parent=None):
        super().__init__(parent=parent)
        self.key = key
        self.input_widget = QComboBox()
        self.input_widget.addItem("none")
        self.input_widget.addItems(value)
        self.input_widget.currentIndexChanged.connect(self.editingFinished.emit)
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(QLabel(label))
        self.layout.addWidget(self.input_widget)

    def reset(self):
        self.input_widget.setCurrentIndex(-1)

    def get_params(self):
        return {self.key: self.input_widget.currentText()}


class BooleanParam(ComboBoxParam):
    def __init__(self, key, value, label, parent=None):
        super().__init__(key, ["True", "False"], label, parent)

    def get_params(self):
        return {self.key: bool(self.input_widget.currentText())}


def AutoParam(key, value, label, parent=None):
    if value in (int, float, str):
        return LineEditParam(key, value, label, parent)
    elif isinstance(value, list):
        return ComboBoxParam(key, value, label, parent)
    elif value is bool:
        return BooleanParam(key, value, label, parent)


def make_parameter_layout(parent, layout_orientation="v", **kwargs):
    if layout_orientation == "v":
        input_layout = QVBoxLayout()
    else:
        input_layout = QHBoxLayout()
    input_widgets = {}
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            labelStr = value[0]
            value = value[1]
        else:
            labelStr = key
        input_widget = AutoParam(key, value, labelStr)
        input_widget.editingFinished.connect(parent.check_plan_ready)
        input_widgets[key] = input_widget
        input_layout.addWidget(input_widget)
    return input_layout, input_widgets


class PlanWidget(QWidget):
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

        self.input_widgets = {}
        self.initial_kwargs = kwargs
        self.setup_widget()

    def current_plan_changed(self, idx):
        plan_display = self.plan_combo_list.currentText()
        self.current_plan = self.plans[plan_display]

    def setup_widget(self):
        if isinstance(self.plans, dict):
            self.plan_combo_list = QComboBox()
            for display_key in self.plans.keys():
                self.plan_combo_list.addItem(display_key)
            self.plan_combo_list.currentIndexChanged.connect(self.current_plan_changed)
            h = QHBoxLayout()
            h.addWidget(QLabel("Plan Subtype"))
            h.addWidget(self.plan_combo_list)
            self.basePlanLayout.addLayout(h)

        if self.initial_kwargs:
            input_layout, input_widgets = make_parameter_layout(
                self, **self.initial_kwargs
            )
            self.layout.addLayout(input_layout)
            self.input_widgets.update(input_widgets)

    def get_params(self):
        """
        Get parameters from the input widgets.

        Returns
        -------
        dict
            A dictionary of parameters.
        """
        params = {}
        for widget in self.input_widgets.values():
            params.update(widget.get_params())
        return params

    def check_plan_ready(self):
        checks = [widget.check_ready() for widget in self.input_widgets.values()]
        if all(checks):
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def clear_layout(self):
        print("Clearing basePlanLayout")
        for i in reversed(range(self.basePlanLayout.count())):
            widget = self.basePlanLayout.itemAt(i).widget()
            print(f"Trying to remove widget {i}")
            if widget is not None:
                # remove it from the layout list
                print(f"Removing widget {i}")
                self.basePlanLayout.removeWidget(widget)
                # remove it from the gui
                widget.setParent(None)
        print("Clearing Layout")
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            print(f"Trying to remove widget {i}")
            if widget is not None:
                print(f"Removing widget {i}")
                # remove it from the layout list
                self.layout.removeWidget(widget)
                # remove it from the gui
                widget.setParent(None)

    def reset(self):
        for widget in self.input_widgets.values():
            widget.reset()


class PlanModifier(PlanWidget):
    def __init__(self, model, wrapper, **kwargs):
        self._wrapper = wrapper
        super().__init__(model, **kwargs)

    def get_params(self):
        return self._wrapper, super().get_params()
