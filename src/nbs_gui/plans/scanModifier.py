from .base import ParamGroup, SpinBoxParam, LineEditParam


class ScanModifierParam(ParamGroup):
    def __init__(self, parent=None):
        super().__init__(parent, "Scan Setup")
        self.add_param(SpinBoxParam("repeat", "Repeat", minimum=1, default=1))
        self.add_param(LineEditParam("comment", str, "Comment"))
        self.add_param(LineEditParam("group_name", str, "Group Name"))


class BeamlineModifierParam(ParamGroup):
    def __init__(self, parent=None):
        super().__init__(parent, "Beamline Setup")

        self.add_param(LineEditParam("exit_slit", float, "Exit Slit"))
        self.add_param(LineEditParam("polarization", float, "Polarization"))
        self.add_param(LineEditParam("energy", float, "Energy"))
