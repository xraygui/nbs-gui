from .base import PlanWidgetBase, AutoParamGroup
from .sampleModifier import SampleSelectWidget
from .scanModifier import ScanModifierParam, BeamlineModifierParam
from qtpy.QtWidgets import QGridLayout, QWidget


class NBSPlanWidget(PlanWidgetBase):
    def __init__(
        self,
        model,
        parent=None,
        plans="",
        sample_setup=True,
        beamline_setup=True,
        plan_setup=True,
        **kwargs,
    ):
        self.initial_kwargs = kwargs
        super().__init__(model, parent, plans)

    def setup_widget(self):
        print("NBSPlanWidget setup Widget")
        super().setup_widget()
        print("Making gridlayout")
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)
        print("Initialize scan widget")
        self.scan_widget = AutoParamGroup(
            self, title="Scan Parameters", **self.initial_kwargs
        )
        print("Initialize scan modifier")
        self.scan_modifier = ScanModifierParam(self)
        print("Initialize bl widget")
        self.bl_modifier = BeamlineModifierParam(self)
        print("Initialize sample widget")
        self.sample_select = SampleSelectWidget(self.model, self)
        print("Connect scanwidget")
        self.scan_widget.editingFinished.connect(self.check_plan_ready)
        print("Connect sample widget")
        self.sample_select.editingFinished.connect(self.check_plan_ready)
        # Create placeholder widgets for the 2x2 grid
        print("Adding widgets to grid")
        self.grid_layout.addWidget(self.scan_widget, 0, 0)
        self.grid_layout.addWidget(self.sample_select, 0, 1)
        self.grid_layout.addWidget(self.bl_modifier, 1, 1)
        self.grid_layout.addWidget(self.scan_modifier, 1, 0)
        print("ADding widgets to params")
        self.params.append(self.scan_widget)
        self.params.append(self.scan_modifier)
        self.params.append(self.bl_modifier)
        self.params.append(self.sample_select)
        print("NBSPlanWidget setup Widget finished")
