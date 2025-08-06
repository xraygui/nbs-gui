from .base import BasicPlanWidget
from .planParam import AutoParamGroup
from .sampleModifier import SampleSelectWidget
from .scanModifier import ScanModifierParam, BeamlineModifierParam
from qtpy.QtWidgets import QGridLayout, QWidget, QHBoxLayout, QVBoxLayout


class NBSPlanWidget(BasicPlanWidget):
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
        print("Initializing NBSPlanWidget Super")
        super().__init__(model, parent, plans)
        print("Done initializing NBSPlanWidget Super")

    def setup_widget(self):
        print("NBSPlanWidget setup Widget")
        super().setup_widget()
        self.scan_widget = AutoParamGroup(
            self, title="Scan Parameters", **self.initial_kwargs
        )
        self.params.append(self.scan_widget)
        self.scan_widget.editingFinished.connect(self.check_plan_ready)

        if self.plan_setup:
            self.scan_modifier = ScanModifierParam(self.model, self)
            self.params.append(self.scan_modifier)
        if self.beamline_setup:
            self.bl_modifier = BeamlineModifierParam(self.model, self)
            self.params.append(self.bl_modifier)

        if self.sample_setup:
            self.sample_select = SampleSelectWidget(self.model, self)
            self.sample_select.editingFinished.connect(self.check_plan_ready)
            self.params.append(self.sample_select)

        # Create placeholder widgets for the 2x2 grid
        self.widget_layout = QHBoxLayout()

        if self.layout_style == 2:
            self.layout.addWidget(self.scan_widget)
            if self.sample_setup:
                self.widget_layout.addWidget(self.sample_select)
            if self.plan_setup:
                self.widget_layout.addWidget(self.scan_modifier)
            if self.beamline_setup:
                self.widget_layout.addWidget(self.bl_modifier)
        else:
            self.widget_layout.addWidget(self.scan_widget)
            if self.sample_setup:
                self.widget_layout.addWidget(self.sample_select)
            if self.plan_setup and self.beamline_setup:
                vlayout = QVBoxLayout()
                vlayout.addWidget(self.scan_modifier)
                vlayout.addWidget(self.bl_modifier)
                self.widget_layout.addLayout(vlayout)
            elif self.plan_setup:
                self.widget_layout.addWidget(self.scan_modifier)
            elif self.beamline_setup:
                self.widget_layout.addWidget(self.bl_modifier)

        if self.widget_layout.count() > 0:
            self.layout.addLayout(self.widget_layout)
        else:
            del self.widget_layout

        print("NBSPlanWidget setup Widget finished")
