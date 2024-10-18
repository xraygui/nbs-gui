from .base import PlanWidgetBase, AutoParamGroup
from .sampleModifier import SampleSelectWidget
from .scanModifier import ScanModifierParam, BeamlineModifierParam
from qtpy.QtWidgets import QGridLayout, QWidget, QHBoxLayout, QVBoxLayout


class NBSPlanWidget(PlanWidgetBase):
    def __init__(
        self,
        model,
        parent=None,
        plans="",
        sample_setup=True,
        beamline_setup=True,
        plan_setup=True,
        layout_style=1,
        **kwargs,
    ):
        self.initial_kwargs = kwargs
        self.sample_setup = sample_setup
        self.beamline_setup = beamline_setup
        self.plan_setup = plan_setup
        self.layout_style = layout_style
        super().__init__(model, parent, plans)

    def setup_widget(self):
        print("NBSPlanWidget setup Widget")
        super().setup_widget()
        self.scan_widget = AutoParamGroup(
            self, title="Scan Parameters", **self.initial_kwargs
        )
        self.scan_modifier = ScanModifierParam(self)
        self.bl_modifier = BeamlineModifierParam(self)
        self.sample_select = SampleSelectWidget(self.model, self)
        self.scan_widget.editingFinished.connect(self.check_plan_ready)
        self.sample_select.editingFinished.connect(self.check_plan_ready)
        # Create placeholder widgets for the 2x2 grid

        self.params.append(self.scan_widget)
        self.params.append(self.scan_modifier)
        self.params.append(self.bl_modifier)
        self.params.append(self.sample_select)

        self.widget_layout = QHBoxLayout()

        if self.layout_style == 2:
            self.layout.addWidget(self.scan_widget)
            self.widget_layout.addWidget(self.sample_select)
            self.widget_layout.addWidget(self.scan_modifier)
            self.widget_layout.addWidget(self.bl_modifier)
        else:
            self.widget_layout.addWidget(self.scan_widget)
            self.widget_layout.addWidget(self.sample_select)
            vlayout = QVBoxLayout()
            vlayout.addWidget(self.scan_modifier)
            vlayout.addWidget(self.bl_modifier)
            self.widget_layout.addLayout(vlayout)
        self.layout.addLayout(self.widget_layout)

        print("NBSPlanWidget setup Widget finished")
