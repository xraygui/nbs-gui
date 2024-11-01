from qtpy.QtWidgets import (
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
)
from qtpy.QtCore import Signal, Qt
from bluesky_queueserver_api import BPlan, BFunc
from .planParam import DynamicComboParam
from .nbsPlan import NBSPlanWidget


class XASParam(DynamicComboParam):
    signal_update_region = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xas_plans = {}
        self.input_widget.currentIndexChanged.connect(self.update_region)

    def update_options(self, xas_plans):
        current_text = self.input_widget.currentText()
        self.xas_plans = xas_plans
        self.input_widget.clear()
        self.input_widget.addItem(self.dummy_text)

        for key, plan_info in xas_plans.items():
            display_label = plan_info.get("name", key)
            self.input_widget.addItem(str(display_label), userData=key)

        index = self.input_widget.findText(current_text)
        self.input_widget.setCurrentIndex(index if index >= 0 else 0)

    def update_region(self):
        key = self.input_widget.currentData()
        plan_info = self.xas_plans.get(key, {})
        region = str(plan_info.get("region", ""))
        self.signal_update_region.emit(region)

    def make_region_label(self):
        label = QLabel("")
        self.signal_update_region.connect(label.setText)
        return label

    def get_params(self):
        if self.input_widget.currentIndex() != 0:
            data = self.input_widget.currentData()
            print(f"Returning XAS {data}")
            return {"plan": data}
        return {}


class XASPlanWidget(NBSPlanWidget):
    signal_update_xas = Signal(object)

    def __init__(self, model, parent=None):
        print("Initializing XAS")
        self.display_name = "XAS"
        super().__init__(
            model,
            parent,
            "dummy",
            layout_style=2,
            dwell={
                "type": "spinbox",
                "args": {"minimum": 0.1, "value_type": float, "default": 1},
                "label": "Dwell Time per Step (s)",
            },
        )
        self.signal_update_xas.connect(self.update_xas)
        self.user_status.register_signal("XAS_PLANS", self.signal_update_xas)
        print("XAS Initialized")

        # Add Load XAS button
        self.load_xas_button = QPushButton("Load XAS regions from file", self)
        self.load_xas_button.clicked.connect(self.load_xas_file)
        self.basePlanLayout.addWidget(self.load_xas_button)

    def setup_widget(self):
        super().setup_widget()

        self.xas_plans = {}
        self.edge_selection = XASParam(
            "edge", "XAS Scan", "Select XAS Plan", parent=self
        )
        self.scan_widget.add_param(self.edge_selection, 0)
        self.scan_widget.add_row(
            QLabel("Scan Region"), self.edge_selection.make_region_label(), 1
        )
        self.user_status.register_signal("XAS_PLANS", self.signal_update_xas)
        self.user_status.register_signal(
            "XAS_PLANS", self.edge_selection.signal_update_options
        )

    def load_xas_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("TOML files (*.toml)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                # Placeholder function name, to be replaced later
                item = BFunc("load_xas", file_path)
                # print(f"Submitted XAS file: {file_path}")
                try:
                    self.run_engine_client._client.function_execute(item)
                    return True
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "XAS Load Error",
                        f"Failed to load {file_path}: {str(e)}",
                        QMessageBox.Ok,
                    )
                    return False

    def check_plan_ready(self):
        """
        Check if all selections have been made and emit the plan_ready signal if they have.
        """
        # print("Checking XAS Plan")
        if self.sample_select.check_ready() and self.edge_selection.check_ready():
            # print("XAS Ready to Submit")
            self.plan_ready.emit(True)
        else:
            # print("XAS not ready")
            self.plan_ready.emit(False)

    def update_xas(self, plan_dict):
        self.xas_plans = plan_dict
        self.edge_selection.signal_update_options.emit(self.xas_plans)
        self.widget_updated.emit()

    def create_plan_items(self):
        params = self.get_params()
        plan = params.pop("plan")
        samples = params.pop("samples", [{}])
        items = []
        for s in samples:
            item = BPlan(plan, **s, **params)
            items.append(item)
        return items
