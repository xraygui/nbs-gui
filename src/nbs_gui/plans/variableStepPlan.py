from qtpy.QtCore import Signal
from bluesky_queueserver_api import BPlan
from .nbsPlan import NBSPlanWidget
from .planParam import LineEditParam
from .variableParamGroup import VariableParamGroupBase


class VariableStepParam(VariableParamGroupBase):

    def _make_start_param(self):
        start = LineEditParam(
            "start", float, "Start", "Motor Start Position", parent=self
        )
        start.label_text = "Start"
        return start

    def _make_param_pair(self):
        index = (len(self.params) + 1) // 2
        step = LineEditParam(
            f"step_{index}",
            float,
            f"Start {index}",
            f"Motor step size to take between start and end of segment {index}",
            self,
        )
        step.label_text = f"Step {index}"
        stop = LineEditParam(
            f"stop_{index}",
            float,
            f"Stop {index}",
            f"Motor endpoint {index}",
            self,
        )
        stop.label_text = f"Stop {index}"
        return step, stop

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

    def create_plan_items(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])
        args = params.pop("args")
        motor = params.pop("motor")
        items = []
        for sample in samples:
            item = BPlan(
                self.current_plan,
                motor,
                *args,
                **params,
                **sample,
            )
            items.append(item)
        return items
