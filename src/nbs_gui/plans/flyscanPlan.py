from .nbsPlan import NBSPlanWidget
from bluesky_queueserver_api import BPlan


class FlyscanWidget(NBSPlanWidget):
    display_name = "Fly Scan"

    def __init__(self, model, parent=None):
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
            speed=float,
            period=float,
        )

    def submit_plan(self):
        params = self.get_params()
        samples = params.pop("samples", [{}])
        motor = params.pop("motor")
        args = [params.pop("start"), params.pop("stop")]
        speed = params.pop("speed", None)
        if speed is not None:
            args.append(speed)
        for sample in samples:
            item = BPlan(
                self.current_plan,
                motor,
                *args,
                **params,
                **sample,
            )
        self.run_engine_client.queue_item_add(item=item)
