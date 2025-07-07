import csv
from qtpy.QtWidgets import QWidget, QVBoxLayout, QTableView, QMessageBox
from qtpy.QtCore import Qt, QAbstractTableModel, Signal
from bluesky_queueserver_api import BPlan
from typing import List, Dict, Any


class PlanQueueTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._headers = list(data[0].keys()) if data else []

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return str(list(self._data[index.row()].values())[index.column()])
        return None

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._headers[section])
            if orientation == Qt.Vertical:
                return str(section + 1)
        return None


class PlanLoaderWidgetBase(QWidget):
    plan_ready = Signal(bool)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.run_engine = model.run_engine
        self.user_status = model.user_status
        self.layout = QVBoxLayout(self)
        self.table_view = QTableView(self)
        self.layout.addWidget(self.table_view)
        self.plan_queue_data = []

    def load_plan_file(self, filename: str):
        """
        Load CSV file and generate plan queue.

        Parameters:
        filename (str): Path to the CSV file

        Returns:
        None
        """
        try:
            with open(filename, "r", newline="") as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                self.plan_queue_data = list(reader)
            self._update_table_view()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV file: {str(e)}")
        self.check_plan_ready()

    def _update_table_view(self):
        """
        Update the QTableView with the current plan queue data.
        """
        model = PlanQueueTableModel(self.plan_queue_data)
        self.table_view.setModel(model)

    def clear_plan_queue(self):
        """
        Clear the current plan queue.
        """
        self.plan_queue_data = []
        self._update_table_view()
        self.check_plan_ready()

    def submit_plan(self, item):
        """
        Submit a plan item to the run engine client.

        Parameters
        ----------
        item : BPlan
            The plan item to be submitted.

        Returns
        -------
        bool
            True if the submission was successful, False otherwise.
        """
        try:
            self.run_engine.queue_item_add(item=item)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Submission Error",
                f"Failed to submit plan: {str(e)}",
                QMessageBox.Ok,
            )
            return False

    def submit_all_plans(self):
        """
        Create and submit all plan items.
        """
        plan_items = self.create_plan_items()
        for item in plan_items:
            if not self.submit_plan(item):
                break  # Stop submitting if an error occurs

    def stage_plan(self, item):
        """
        Stage a plan item.
        """
        try:
            self.model.queue_staging.queue_item_add(item=item)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Plan Staging Error",
                f"Failed to stage plan: {str(e)}",
                QMessageBox.Ok,
            )
            return False

    def stage_all_plans(self):
        """
        Create and stage all plan items.
        """
        plan_items = self.create_plan_items()
        for item in plan_items:
            if not self.stage_plan(item):
                break  # Stop staging if an error occurs

    def check_plan_ready(self):
        if len(self.plan_queue_data) > 0:
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)


class XASPlanLoader(PlanLoaderWidgetBase):
    display_name = "XAS Plans"
    signal_update_xas = Signal(object)
    signal_update_samples = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(model, parent)
        self.xas_plans = {}
        self.signal_update_xas.connect(self.update_xas)
        self.user_status.register_signal("XAS_PLANS", self.signal_update_xas)

        self.signal_update_samples.connect(self.update_samples)
        self.user_status.register_signal("GLOBAL_SAMPLES", self.signal_update_samples)

    def update_xas(self, xas_plans):
        self.xas_plans = xas_plans

    def update_samples(self, sample_dict):
        self.samples = sample_dict

    def get_plan(self, plan_name):
        plan_name = plan_name.lower()
        if plan_name in self.xas_plans:
            return plan_name
        else:
            for plan_key, plan_info in self.xas_plans.items():
                if plan_name in [
                    plan_info.get("name", "").lower(),
                    plan_info.get("edge", "").lower(),
                ]:
                    return plan_key
        raise KeyError(f"{plan_name} not found in list of XAS Plans")

    def create_plan_items(self):
        items = []
        for plan_data in self.plan_queue_data:
            sample_id = plan_data.get("Sample ID")
            plan_name = plan_data.get("Edge")

            try:
                plan = self.get_plan(plan_name)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Plan Generation Error",
                    f"Failed to create plan: {str(e)}",
                    QMessageBox.Ok,
                )
                return []

            if sample_id not in self.samples:
                QMessageBox.critical(
                    self,
                    "Plan Generation Error",
                    f"Sample: {sample_id} not in sample list",
                    QMessageBox.Ok,
                )
                return []

            plan_kwargs = {}
            plan_kwargs["eslit"] = (
                float(plan_data.get("Slit Size", None))
                if plan_data.get("Slit Size") is not None
                else None
            )
            plan_kwargs["sample_position"] = {
                "r": (
                    float(plan_data.get("Angle", None))
                    if plan_data.get("Angle") is not None
                    else None
                )
            }
            plan_kwargs["group_name"] = plan_data.get("Group Name", None)
            plan_kwargs["comment"] = plan_data.get("Comment", None)
            plan_kwargs["repeat"] = int(plan_data.get("Repeat", 1))

            item = BPlan(plan, sample=sample_id, **plan_kwargs)
            items.append(item)
        return items
