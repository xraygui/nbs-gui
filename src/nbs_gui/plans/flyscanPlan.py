from .nbsPlan import NBSPlanWidget
from bluesky_queueserver_api import BPlan


class FlyscanWidget(NBSPlanWidget):
    display_name = "Fly Scan"

    def __init__(self, model, parent=None):
        print("Initializing FlyScan")
        super().__init__(
            model,
            parent=None,
            plans="nbs_fly_scan",
            motor={
                "type": "motor",
                "label": "Motor to Flyscan",
            },
            start=float,
            stop=float,
            speed={
                "type": "spinbox",
                "args": {"value_type": float},
                "label": "Speed",
                "help_text": "Motor speed between start and stop",
            },
            period={
                "type": "spinbox",
                "args": {"value_type": float},
                "label": "Detector Period (s)",
                "help_text": "Read non-flyer detectors every X seconds during flyscan",
            },
        )
        print("Done initializing FlyScan")

    def create_plan_items(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])
        motor = params.pop("motor")
        args = [params.pop("start"), params.pop("stop")]
        speed = params.pop("speed", None)
        if speed is not None:
            args.append(speed)
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
