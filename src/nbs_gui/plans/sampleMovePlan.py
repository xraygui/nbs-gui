from qtpy.QtCore import Signal
from bluesky_queueserver_api import BPlan
from .base import BasicPlanWidget
from .sampleModifier import SampleComboParam


class SampleMovePlan(BasicPlanWidget):
    """
    Widget for moving samples to specified positions with optional offsets.

    Parameters
    ----------
    model : object
        The model object containing run_engine and user_status
    parent : QWidget, optional
        Parent widget
    """

    def __init__(self, model, parent=None, **kwargs):
        super().__init__(model, parent, "move_sample")
        self.display_name = "Move Sample"

    def setup_widget(self):
        print("Setting up SampleMovePlan widget")
        super().setup_widget()
        print("Super().setup_widget() completed")
        self.sample_param = SampleComboParam(self)
        self.params = [self.sample_param]
        self.sample_param.editingFinished.connect(self.check_plan_ready)
        self.basePlanLayout.addWidget(self.sample_param)

        self.samples = self.user_status.get_redis_dict("GLOBAL_SAMPLES")
        if self.samples is not None:
            self.samples.changed.connect(self.update_samples)
        self.update_samples()

    def update_samples(self):
        # print("Got Sample Update")
        self.sample_param.update_samples(self.samples)

    def create_plan_items(self):
        """
        Create the plan items for submission

        Returns
        -------
        list
            List of plan items
        """
        sample_params = self.sample_param.get_params()
        sample_params = sample_params[0]
        sample = sample_params.pop("sample")
        sample_position = sample_params.pop("sample_position", {})

        plan = BPlan("move_sample", sample, **sample_position)

        return [plan]
