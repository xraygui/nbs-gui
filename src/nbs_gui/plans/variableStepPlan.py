from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
from bluesky_queueserver_api import BPlan
from .nbsPlan import NBSPlanWidget
from .base import LineEditParam, BaseParam


class VariableStepParam(BaseParam):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.label_text = "Variable Step Arguments"
        self.params = []

        # Layout for parameters
        self.param_layout = QHBoxLayout()
        self.layout.addLayout(self.param_layout)
        start = LineEditParam("start", float, "Start", self)
        start.label_text = "Start"
        param_layout = QVBoxLayout()
        label = QLabel(start.label_text)
        param_layout.addWidget(label)
        param_layout.addWidget(start)
        self.param_layout.addLayout(param_layout)
        self.params.append(start)

        # Add initial parameters
        self.add_param_pair()

        # Button layout
        button_layout = QVBoxLayout()
        self.plus_button = QPushButton("+")
        self.minus_button = QPushButton("-")
        button_layout.addWidget(self.plus_button)
        button_layout.addWidget(self.minus_button)
        self.layout.addLayout(button_layout)

        # Connect buttons
        self.plus_button.clicked.connect(self.add_param_pair)
        self.minus_button.clicked.connect(self.remove_param_pair)

        # Initially disable minus button
        self.minus_button.setEnabled(False)

    def add_param_pair(self):
        index = (len(self.params) + 1) // 2
        stop = LineEditParam(f"stop_{index}", float, f"Stop {index}", self)
        stop.label_text = f"Stop {index}"
        step = LineEditParam(f"step_{index}", float, f"Start {index}", self)
        step.label_text = f"Step {index}"
        for param in [stop, step]:
            param_layout = QVBoxLayout()
            label = QLabel(param.label_text)
            param_layout.addWidget(label)
            param_layout.addWidget(param)
            self.param_layout.addLayout(param_layout)

        self.params.extend([stop, step])

        # Enable minus button if we have more than one pair
        if len(self.params) > 3:
            self.minus_button.setEnabled(True)

        self.editingFinished.emit()
        stop.editingFinished.connect(self.editingFinished)
        step.editingFinished.connect(self.editingFinished)

    def remove_param_pair(self):
        if len(self.params) > 3:
            for _ in range(2):
                param = self.params.pop()
                layout_item = self.param_layout.takeAt(self.param_layout.count() - 1)
                if layout_item:
                    layout = layout_item.layout()
                    if layout:
                        while layout.count():
                            item = layout.takeAt(0)
                            widget = item.widget()
                            if widget:
                                widget.deleteLater()
                    layout_item.layout().deleteLater()

            # Disable minus button if we're down to one pair
            if len(self.params) == 3:
                self.minus_button.setEnabled(False)

    def reset(self):
        for param in self.params:
            param.reset()

    def get_params(self):
        params = {}
        arglist = []
        for param in self.params:
            param_dict = param.get_params()
            arglist.append(param_dict.get(param.key, None))
        params["args"] = arglist
        return params

    def check_ready(self):
        params = self.get_params()
        print("Checking varscan params")
        print(params)
        return None not in params


class VariableStepWidget(NBSPlanWidget):
    signal_update_motors = Signal(object)
    display_name = "Variable Step Scan"

    def __init__(
        self,
        model,
        parent=None,
        plans="nbs_gscan",
    ):
        print("Initializing Variable Scan")
        super().__init__(
            model,
            parent,
            plans,
            motor={
                "type": "motor",
                "label": "Motor to Move",
            },
            dwell={
                "type": "spinbox",
                "args": {"minimum": 0.1, "value_type": float, "default": 1},
                "label": "Dwell Time per Step (s)",
            },
            layout_style=2,
        )
        self.scan_widget.add_param(VariableStepParam(self))
        print("Variable Scan Initialized")

    def check_plan_ready(self):
        params = self.get_params()
        checks = ["motor" in params, self.scan_widget.check_ready()]
        self.plan_ready.emit(all(checks))

    def submit_plan(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])
        args = params.pop("args")
        motor = params.pop("motor")
        # params["start"],
        # params["end"],
        # params["steps"]
        for sample in samples:
            item = BPlan(
                self.current_plan,
                motor,
                *args,
                **params,
                **sample,
            )
        self.run_engine_client.queue_item_add(item=item)
