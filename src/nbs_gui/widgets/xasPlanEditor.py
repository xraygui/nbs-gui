from qtpy.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QFormLayout,
    QTextEdit,
)
from qtpy.QtCore import Qt, Signal

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

try:
    import tomli_w as toml
except ModuleNotFoundError:
    import tomli_w as toml


class XASPlanEditorWidget(QDialog):
    signal_plans_changed = Signal()

    def __init__(self, parent=None, load_file=None):
        super().__init__(parent)
        self.plans_dict = {}
        self.current_file_path = load_file
        self.has_unsaved_changes = False
        self.setup_ui()
        if self.current_file_path:
            self._load_file(self.current_file_path)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Load TOML File")
        self.save_button = QPushButton("Save TOML File")
        self.save_as_button = QPushButton("Save As...")
        self.add_button = QPushButton("Add Plan")
        self.delete_button = QPushButton("Delete Plan")

        self.load_button.clicked.connect(self.load_file)
        self.save_button.clicked.connect(self.save_file)
        self.save_as_button.clicked.connect(self.save_as_file)
        self.add_button.clicked.connect(self.add_plan)
        self.delete_button.clicked.connect(self.delete_plan)

        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.save_as_button)
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)

        main_layout.addLayout(button_layout)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(
            ["Key", "Name", "Element", "Edge", "Region"]
        )
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SingleSelection)
        self.table_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.table_widget.itemChanged.connect(self.on_table_item_changed)
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.table_widget)

        self.editor_widget = self.create_editor_widget()
        splitter.addWidget(self.editor_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.update_delete_button_state()

    def create_editor_widget(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        form_layout = QFormLayout()

        self.key_edit = QLineEdit()
        self.key_edit.setReadOnly(True)
        form_layout.addRow("Key:", self.key_edit)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_editor_changed)
        form_layout.addRow("Name:", self.name_edit)

        self.element_edit = QLineEdit()
        self.element_edit.textChanged.connect(self.on_editor_changed)
        form_layout.addRow("Element:", self.element_edit)

        self.edge_edit = QLineEdit()
        self.edge_edit.textChanged.connect(self.on_editor_changed)
        form_layout.addRow("Edge:", self.edge_edit)

        self.region_edit = QTextEdit()
        self.region_edit.setPlaceholderText(
            "Enter region as list, e.g., [2185, 2285, 0.5]"
        )
        self.region_edit.textChanged.connect(self.on_editor_changed)
        form_layout.addRow("Region:", self.region_edit)

        layout.addLayout(form_layout)
        layout.addStretch()

        self.apply_button = QPushButton("Apply Changes")
        self.apply_button.clicked.connect(self.apply_changes)
        self.apply_button.setEnabled(False)
        layout.addWidget(self.apply_button)

        return widget

    def load_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("TOML files (*.toml)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self._load_file(file_path)

    def _load_file(self, file_path):
        try:
            with open(file_path, "rb") as f:
                self.plans_dict = tomllib.load(f)
            self.current_file_path = file_path
            self.has_unsaved_changes = False
            self.populate_table()
            self.setWindowTitle(f"XAS Plan Editor - {file_path}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load {file_path}:\n{str(e)}",
                QMessageBox.Ok,
            )

    def save_file(self):
        if self.current_file_path is None:
            self.save_as_file()
        else:
            self.save_to_file(self.current_file_path)

    def save_as_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("TOML files (*.toml)")
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                if not file_path.endswith(".toml"):
                    file_path += ".toml"
                self.current_file_path = file_path
                self.save_to_file(file_path)

    def save_to_file(self, file_path):
        try:
            with open(file_path, "w") as f:
                toml.dump(self.plans_dict, f)
            self.setWindowTitle(f"XAS Plan Editor - {file_path}")
            self.has_unsaved_changes = False
            QMessageBox.information(
                self,
                "Save Successful",
                f"Plans saved to {file_path}",
                QMessageBox.Ok,
            )
            self.signal_plans_changed.emit()
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save {file_path}:\n{str(e)}",
                QMessageBox.Ok,
            )
            return False

    def populate_table(self):
        self.table_widget.setRowCount(len(self.plans_dict))
        self.table_widget.blockSignals(True)

        for row, (key, plan_data) in enumerate(sorted(self.plans_dict.items())):
            key_item = QTableWidgetItem(str(key))
            key_item.setData(Qt.UserRole, key)
            self.table_widget.setItem(row, 0, key_item)
            self.table_widget.setItem(
                row, 1, QTableWidgetItem(str(plan_data.get("name", "")))
            )
            self.table_widget.setItem(
                row, 2, QTableWidgetItem(str(plan_data.get("element", "")))
            )
            self.table_widget.setItem(
                row, 3, QTableWidgetItem(str(plan_data.get("edge", "")))
            )
            region = plan_data.get("region", [])
            region_str = str(region) if isinstance(region, list) else str(region)
            self.table_widget.setItem(row, 4, QTableWidgetItem(region_str))

        self.table_widget.blockSignals(False)
        self.update_delete_button_state()

    def on_selection_changed(self):
        selected_rows = self.table_widget.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            key_item = self.table_widget.item(row, 0)
            if key_item:
                key = key_item.text()
                plan_data = self.plans_dict.get(key, {})
                self.load_plan_to_editor(key, plan_data)
        else:
            self.clear_editor()

    def load_plan_to_editor(self, key, plan_data):
        self.key_edit.setText(key)
        self.name_edit.setText(str(plan_data.get("name", "")))
        self.element_edit.setText(str(plan_data.get("element", "")))
        self.edge_edit.setText(str(plan_data.get("edge", "")))
        region = plan_data.get("region", [])
        region_str = str(region) if isinstance(region, list) else str(region)
        self.region_edit.setPlainText(region_str)
        self.apply_button.setEnabled(False)

    def clear_editor(self):
        self.key_edit.clear()
        self.name_edit.clear()
        self.element_edit.clear()
        self.edge_edit.clear()
        self.region_edit.clear()
        self.apply_button.setEnabled(False)

    def on_editor_changed(self):
        self.apply_button.setEnabled(True)
        self.has_unsaved_changes = True

    def on_table_item_changed(self, item):
        if self.table_widget.signalsBlocked():
            return

        row = item.row()
        key_item = self.table_widget.item(row, 0)
        if not key_item:
            return

        col = item.column()
        if col == 0:
            old_key = key_item.data(Qt.UserRole)
            if not old_key:
                old_key = key_item.text()
            new_key = key_item.text().strip()

            if not new_key:
                QMessageBox.warning(
                    self,
                    "Invalid Key",
                    "Plan key cannot be empty.",
                    QMessageBox.Ok,
                )
                self.table_widget.blockSignals(True)
                key_item.setText(old_key)
                self.table_widget.blockSignals(False)
                return

            if new_key == old_key:
                return

            if new_key in self.plans_dict:
                QMessageBox.warning(
                    self,
                    "Duplicate Key",
                    (
                        f"Plan key '{new_key}' already exists. "
                        "Please choose a different key."
                    ),
                    QMessageBox.Ok,
                )
                self.table_widget.blockSignals(True)
                key_item.setText(old_key)
                self.table_widget.blockSignals(False)
                return

            if old_key in self.plans_dict:
                plan_data = self.plans_dict.pop(old_key)
                self.plans_dict[new_key] = plan_data
                key_item.setData(Qt.UserRole, new_key)
                self.has_unsaved_changes = True
                self.populate_table()
                for r in range(self.table_widget.rowCount()):
                    k_item = self.table_widget.item(r, 0)
                    if k_item and k_item.text() == new_key:
                        self.table_widget.selectRow(r)
                        self.load_plan_to_editor(new_key, plan_data)
                        break
            return

        key = key_item.text()
        if key not in self.plans_dict:
            return

        if col == 1:
            self.plans_dict[key]["name"] = item.text()
            self.has_unsaved_changes = True
        elif col == 2:
            self.plans_dict[key]["element"] = item.text()
            self.has_unsaved_changes = True
        elif col == 3:
            self.plans_dict[key]["edge"] = item.text()
            self.has_unsaved_changes = True
        elif col == 4:
            try:
                region_str = item.text().strip()
                if region_str:
                    region = eval(region_str)
                    if isinstance(region, list) and len(region) >= 2:
                        self.plans_dict[key]["region"] = [float(x) for x in region]
                        self.has_unsaved_changes = True
            except Exception:
                pass

        selected_rows = self.table_widget.selectedIndexes()
        if selected_rows and selected_rows[0].row() == row:
            plan_data = self.plans_dict[key]
            self.load_plan_to_editor(key, plan_data)

    def apply_changes(self):
        selected_rows = self.table_widget.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        key_item = self.table_widget.item(row, 0)
        if not key_item:
            return

        key = key_item.text()
        if key not in self.plans_dict:
            return

        plan_data = self.plans_dict[key]
        plan_data["name"] = self.name_edit.text()
        plan_data["element"] = self.element_edit.text()
        plan_data["edge"] = self.edge_edit.text()

        try:
            region_str = self.region_edit.toPlainText().strip()
            if not region_str:
                raise ValueError("Region cannot be empty")
            region = eval(region_str)
            if not isinstance(region, list):
                raise ValueError("Region must be a list")
            if len(region) < 2:
                raise ValueError("Region must have at least 2 values (start, stop)")
            plan_data["region"] = [float(x) for x in region]
        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid Region",
                ("Region must be a valid Python list of numbers.\n" f"Error: {str(e)}"),
                QMessageBox.Ok,
            )
            return

        self.populate_table()
        self.table_widget.selectRow(row)
        self.apply_button.setEnabled(False)

    def add_plan(self):
        new_key = f"plan_{len(self.plans_dict) + 1}"
        while new_key in self.plans_dict:
            new_key = f"plan_{len(self.plans_dict) + 1}"

        self.plans_dict[new_key] = {
            "name": "",
            "element": "",
            "edge": "",
            "region": [],
        }
        self.has_unsaved_changes = True

        self.populate_table()
        for row in range(self.table_widget.rowCount()):
            key_item = self.table_widget.item(row, 0)
            if key_item and key_item.text() == new_key:
                self.table_widget.selectRow(row)
                self.table_widget.editItem(key_item)
                break

    def delete_plan(self):
        selected_rows = self.table_widget.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        key_item = self.table_widget.item(row, 0)
        if not key_item:
            return

        key = key_item.text()
        reply = QMessageBox.question(
            self,
            "Delete Plan",
            f"Are you sure you want to delete plan '{key}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            del self.plans_dict[key]
            self.has_unsaved_changes = True
            self.populate_table()
            self.clear_editor()
            if self.table_widget.rowCount() > 0:
                if row < self.table_widget.rowCount():
                    self.table_widget.selectRow(row)
                else:
                    self.table_widget.selectRow(self.table_widget.rowCount() - 1)

    def update_delete_button_state(self):
        self.delete_button.setEnabled(len(self.plans_dict) > 0)

    def closeEvent(self, event):
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )

            if reply == QMessageBox.Save:
                if self.current_file_path is None:
                    self.save_as_file()
                    if self.current_file_path is None:
                        event.ignore()
                        return
                    if not self.has_unsaved_changes:
                        event.accept()
                    else:
                        event.ignore()
                else:
                    if self.save_to_file(self.current_file_path):
                        event.accept()
                    else:
                        event.ignore()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    import argparse
    from qtpy.QtWidgets import QApplication

    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="File to load", nargs="?")
    args = parser.parse_args()

    app = QApplication([])

    editor = XASPlanEditorWidget(load_file=args.file)
    editor.setWindowTitle("XAS Plan Editor")
    editor.resize(1000, 600)

    editor.exec_()


if __name__ == "__main__":
    main()
