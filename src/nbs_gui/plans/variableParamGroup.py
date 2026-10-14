from qtpy.QtCore import Signal
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
from bluesky_queueserver_api import BPlan
from .nbsPlan import NBSPlanWidget
from .planParam import LineEditParam, ParamGroupBase

class VariableParamGroupBase(ParamGroupBase, QWidget):

    def __init__(self, parent=None):
        # print("Initializing Variable Step Param")
        super().__init__(parent=parent)
        # print("Initialized VarStepParam Super")
        self.label_text = "Variable Arguments"

        # Layout for parameters
        self.layout = QHBoxLayout(self)
        self.param_layout = QHBoxLayout()
        self.layout.addLayout(self.param_layout)
        start = self._make_start_param()
        super().add_param(start)

        param_layout = QVBoxLayout()
        label = QLabel(start.label_text)
        param_layout.addWidget(label)
        param_layout.addWidget(start)
        self.param_layout.addLayout(param_layout)
        # print("Adding start")

        # Add initial parameters
        self.add_param_pair()

        # Button layout
        button_layout = QVBoxLayout()
        self.plus_button = QPushButton("+")
        self.minus_button = QPushButton("-")
        button_layout.addWidget(self.plus_button)
        button_layout.addWidget(self.minus_button)
        self.layout.addLayout(button_layout)

        # Connect buttons
        self.plus_button.clicked.connect(self.add_param_pair)
        self.minus_button.clicked.connect(self.remove_param_pair)

        # Initially disable minus button
        self.minus_button.setEnabled(False)

    def _make_start_param(self):
        pass

    def _make_param_pair(self):
        pass

    def add_param_pair(self):
        # print("Adding Param Pair")

        param1, param2 = self._make_param_pair()
        super().add_param(param1)
        super().add_param(param2)
        for param in [param1, param2]:
            param_layout = QVBoxLayout()
            label = QLabel(param.label_text)
            param_layout.addWidget(label)
            param_layout.addWidget(param)
            self.param_layout.addLayout(param_layout)

        # self.params.extend([stop, step])

        # Enable minus button if we have more than one pair
        if len(self.params) > 3:
            self.minus_button.setEnabled(True)

        self.editingFinished.emit()
        # print("Done adding param pair")

    def remove_param_pair(self):
        if len(self.params) > 3:
            for _ in range(2):
                param = self.params.pop()
                layout_item = self.param_layout.takeAt(self.param_layout.count() - 1)
                if layout_item:
                    layout = layout_item.layout()
                    if layout:
                        while layout.count():
                            item = layout.takeAt(0)
                            widget = item.widget()
                            if widget:
                                widget.deleteLater()
                    layout_item.layout().deleteLater()

            # Disable minus button if we're down to one pair
            if len(self.params) == 3:
                self.minus_button.setEnabled(False)
        self.editingFinished.emit()

    def get_params(self):
        params = {}
        arglist = []
        for param in self.params:
            param_dict = param.get_params()
            arglist.append(param_dict.get(param.key, None))
        params["args"] = arglist
        return params

    def check_ready(self):
        params = self.get_params()
        # print("Checking varscan params")
        print(params)
        return None not in params
