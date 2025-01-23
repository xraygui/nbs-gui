from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QComboBox,
)


class EnumControl(QWidget):
    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        super().__init__(**kwargs)
        print(f"Initializing EnumControl for model: {model.label}")
        self.model = model
        if orientation == "v":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        box.setContentsMargins(1, 1, 1, 1)
        box.setSpacing(2)
        self.label = QLabel(model.label)
        self.value = QLabel("")
        self.combo = QComboBox()

        self.model.valueChanged.connect(self.setText)
        self.model.enumChanged.connect(self.updateCombo)
        self.combo.currentTextChanged.connect(self.setValue)

        box.addWidget(self.label)
        box.addWidget(self.value)
        box.addWidget(self.combo)
        self.setLayout(box)

        # Initialize the combo box
        self.updateCombo(model.enum_strs)

    def setText(self, val):
        self.value.setText(val)
        index = self.combo.findText(val)
        if index >= 0:
            self.combo.setCurrentIndex(index)

    def updateCombo(self, enum_strs):
        self.combo.clear()
        self.combo.addItems(enum_strs)

    def setValue(self, value):
        self.model.set(value)


class EnumMonitor(QWidget):
    def __init__(self, model, parent_model=None, orientation="v", **kwargs):
        super().__init__(**kwargs)
        print(f"Initializing EnumMonitor for model: {model.label}")
        self.model = model
        if orientation == "v":
            box = QVBoxLayout()
        else:
            box = QHBoxLayout()
        box.setContentsMargins(1, 1, 1, 1)
        box.setSpacing(2)
        self.label = QLabel(model.label)
        self.value = QLabel("")

        self.model.valueChanged.connect(self.setText)

        box.addWidget(self.label)
        box.addWidget(self.value)
        self.setLayout(box)

        # Initialize the value
        self.setText(self.model._value)

    def setText(self, val):
        self.value.setText(str(val))
