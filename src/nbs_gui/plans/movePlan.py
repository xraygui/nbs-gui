from bluesky_queueserver_api import BPlan
from .base import AutoPlanWidget


class MovePlanWidget(AutoPlanWidget):
    modifiersAllowed = []

    def __init__(self, model, parent=None):
        print("Initializing Move")
        super().__init__(
            model,
            parent,
            {"Move": "mv", "Relative Move": "mvr"},
            motor={
                "type": "motor",
                "label": "Motor to Move",
            },
            position=float,
        )
        self.display_name = "Movement"
        print("Move Initialized")

    def create_plan_items(self):
        params = self.get_params()
        item = BPlan(self.current_plan, params["motor"], params["position"])
        return [item]
