from qtpy.QtCore import Signal
from bluesky_queueserver_api import BPlan
from .nbsPlan import NBSPlanWidget


class TimescanWidget(NBSPlanWidget):
    display_name = "Time Scan (count)"

    def __init__(self, model, parent=None):
        print("Initializing NBSTimescan")

        super().__init__(
            model,
            parent,
            "nbs_count",
            steps={
                "type": "spinbox",
                "args": {"minimum": 1},
                "label": "Number of points",
            },
            dwell={
                "type": "spinbox",
                "args": {"minimum": 0.1, "value_type": float, "default": 1},
                "label": "Dwell Time per Step (s)",
            },
        )
        # Connect signals

    def check_plan_ready(self):
        params = self.get_params()
        # modifier_params = self.scan_modifier.get_params()

        if (
            "steps" in params
            and self.scan_modifier.check_ready()
            and self.sample_select.check_ready()
        ):
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def submit_plan(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])

        # params["steps"],
        # dwell=params.get("dwell", None),
        # comment=params.get("comment", None),
        for sample in samples:
            item = BPlan(
                self.current_plan,
                md={"scantype": "xes"},
                **params,
                **sample,
            )

            # Add repeat functionality
            repeat = params.get("repeat", 1)
            for _ in range(repeat):
                self.run_engine_client.queue_item_add(item=item)


class ScanPlanWidget(NBSPlanWidget):
    signal_update_motors = Signal(object)
    display_name = "Step Scan"

    def __init__(
        self,
        model,
        parent=None,
        plans={
            "Scan": "nbs_scan",
            "Relative Scan": "nbs_rel_scan",
        },
    ):
        print("Initializing Scan")
        super().__init__(
            model,
            parent,
            plans,
            motor={
                "type": "motor",
                "label": "Motor to Move",
            },
            start=float,
            end=float,
            steps={
                "type": "spinbox",
                "args": {"minimum": 1},
                "label": "Number of points",
            },
            dwell={
                "type": "spinbox",
                "args": {"minimum": 0.1, "value_type": float, "default": 1},
                "label": "Dwell Time per Step (s)",
            },
        )
        print("Scan Initialized")

    def check_plan_ready(self):
        params = self.get_params()
        checks = [
            "motor" in params,
            "start" in params,
            "end" in params,
            "steps" in params,
        ]
        self.plan_ready.emit(all(checks))

    def submit_plan(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])
        # params["motor"],
        # params["start"],
        # params["end"],
        # params["steps"]
        for sample in samples:
            item = BPlan(
                self.current_plan,
                **params,
                **sample,
            )
        self.run_engine_client.queue_item_add(item=item)
