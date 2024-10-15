from qtpy.QtWidgets import (
    QTableView,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QHBoxLayout,
)
from qtpy.QtCore import QAbstractTableModel, Qt, Signal, Slot
from ..plans.base import BasicPlanWidget
from bluesky_queueserver_api import BFunc


class SampleTab(QWidget):
    name = "Samples"

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.model = model

        self.sample_view = QtSampleView(model.user_status, parent=self)
        self.new_sample = NewSampleWidget(model, parent)
        self.layout.addWidget(self.new_sample)
        self.layout.addWidget(self.sample_view)


class NewSampleWidget(BasicPlanWidget):
    def __init__(self, model, parent=None):
        super().__init__(
            model,
            parent,
            sample_id=("Sample ID", str),
            name=("Sample Name", str),
            description=("Description", str),
        )
        self.display_name = "Add New Sample"
        self.submit_button = QPushButton("Add New Sample", self)
        self.submit_button.clicked.connect(self.submit_plan)
        self.submit_button.setEnabled(False)
        self.plan_ready.connect(self.submit_button.setEnabled)
        self.layout.addWidget(self.submit_button)

    def check_plan_ready(self):
        params = self.get_params()

        if "sample_id" in params and "name" in params:
            self.plan_ready.emit(True)
        else:
            self.plan_ready.emit(False)

    def submit_plan(self):
        params = self.get_params()
        item = BFunc(
            "add_sample_to_globals",
            params["sample_id"],
            params["name"],
            "",
            -1,
            0,
            description=params.get("description", ""),
        )
        self.run_engine_client._client.function_execute(item)


class QtSampleView(QTableView):
    signal_update_widget = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.user_status = model.user_status
        try:
            signal_name = self.model.beamline.primary_sampleholder.name
            print(f"Got {signal_name} from beamline model sampleholder")
        except Exception as e:
            print(e)
            signal_name = "MANIP"

        self.signal_update_widget.connect(self.update_md)
        self.user_status.register_signal(
            signal_name.upper() + "_SAMPLES", self.signal_update_widget
        )
        self.tableModel = DictTableModel({})
        self.setModel(self.tableModel)

    @Slot(object)
    def update_md(self, samples):
        self.tableModel.update(samples)


class DictTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            key = list(self._data.keys())[index.row()]
            key2 = list(self._data[key].keys())[index.column()]
            return str(self._data[key][key2])

    def rowCount(self, index):
        return len(self._data.keys())

    def columnCount(self, index):
        mincol = None
        for k, v in self._data.items():
            if mincol is None:
                mincol = len(v.keys())
            else:
                mincol = min(len(v.keys()), mincol)
        if mincol is None:
            return 0
        else:
            return mincol

    def update(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self._rows = list(self._data.keys())
        if len(self._rows) > 0:
            for k, v in self._data.items():
                self._columns = list(v.keys())
                break
        self.endResetModel()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._columns[section])
            if orientation == Qt.Vertical:
                return self._rows[section]
