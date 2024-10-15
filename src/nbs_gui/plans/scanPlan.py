from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)
from qtpy.QtCore import Signal
from bluesky_queueserver_api import BPlan
from .base import BasicPlanWidget
from .nbsPlan import NBSPlanWidget
from .scanModifier import ScanModifierParam
from .sampleModifier import SampleSelectWidget


class TimescanWidget(NBSPlanWidget):
    display_name = "Time Scan (count)"

    def __init__(self, model, parent=None):
        print("Initializing NBSTimescan")

        super().__init__(
            model,
            parent,
            "nbs_count",
            steps=int,
            dwell=float,
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

        for sample in samples:
            item = BPlan(
                self.current_plan,
                params["steps"],
                dwell=params.get("dwell", None),
                comment=params.get("comment", None),
                md={"scantype": "xes"},
                **samples,
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
        # Make this into a more general base, and then add variants on top of it, i.e,
        # relscan, grid_scan, etc
        print("Initializing Scan")
        super().__init__(
            model,
            parent,
            plans,
            start=float,
            end=float,
            steps=int,
            # dwell=float,
            # group_name=("Group Name", str),
            # comment=str,
        )
        self.signal_update_motors.connect(self.update_motors)
        self.user_status.register_signal(
            "MOTORS_DESCRIPTIONS", self.signal_update_motors
        )
        # Create and add the scan related widgets here
        print("Scan Initialized")

    def setup_widget(self):
        super().setup_widget()
        self.motors = {}
        self.user_status.register_signal(
            "MOTORS_DESCRIPTIONS", self.signal_update_motors
        )
        self.create_scan_modifier()

    def update_motors(self, plan_dict):
        inverted_dict = {}
        for key, value in plan_dict.items():
            if value != "":
                inverted_dict[value] = key
            else:
                inverted_dict[key] = key
        self.motors = inverted_dict
        self.motor_selection.clear()
        self.motor_selection.addItems(self.motors.keys())

    def create_scan_modifier(self):
        self.motor_selection = QComboBox(self)
        self.motor_selection.addItems(self.motors.keys())
        h = QHBoxLayout()
        h.addWidget(QLabel("Motor to Scan"))
        h.addWidget(self.motor_selection)
        self.basePlanLayout.addLayout(h)

    def check_plan_ready(self):
        params = self.get_params()
        check1 = "start" in params
        check2 = "end" in params
        check3 = "steps" in params
        if check1 and check2 and check3:
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def submit_plan(self):
        motor_text = self.motor_selection.currentText()
        motor = self.motors[motor_text]
        params = self.get_params()
        # start = float(self.modifier_input_from.text())
        # end = float(self.modifier_input_to.text())
        # steps = int(self.modifier_input_steps.text())
        item = BPlan(
            self.current_plan,
            motor,
            params["start"],
            params["end"],
            params["steps"],
            dwell=params.get("dwell", None),
            comment=params.get("comment", None),
        )
        self.run_engine_client.queue_item_add(item=item)
