from qtpy.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QLabel,
    QDialog,
    QLineEdit,
    QPushButton,
    QFormLayout,
)
from qtpy.QtCore import Signal, Slot
from bluesky_queueserver_api import BFunc


class StatusBox(QGroupBox):
    signal_update_widget = Signal(object)

    def __init__(self, status_model, title, key, display_keys=None, parent=None):
        """
        Parameters
        ----------
        status_model : object
            Model containing status information
        title : str
            Title for the group box
        key : str
            Key to register signal with model
        display_keys : list, optional
            List of keys to display. If None, displays all keys
        parent : QWidget, optional
            Parent widget
        """
        super().__init__(title, parent)
        print(f"Initializing StatusBox {title}")
        self.model = status_model
        self.display_keys = display_keys
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.signal_update_widget.connect(self.update_md)
        self.model.register_signal(key, self.signal_update_widget)

    @Slot(object)
    def update_md(self, user_md):
        items_in_layout = self.vbox.count()
        i = 0

        # Filter keys if display_keys is specified
        if self.display_keys is not None:
            # Create ordered dict based on display_keys order
            display_items = {}
            for k in self.display_keys:
                if k in user_md:
                    display_items[k] = user_md[k]
        else:
            display_items = user_md

        for k, v in display_items.items():
            if i + 1 > items_in_layout:
                hbox = QHBoxLayout()
                hbox.addWidget(QLabel(str(k)))
                hbox.addWidget(QLabel(str(v)))
                self.vbox.addLayout(hbox)
            else:
                hbox = self.vbox.itemAt(i)
                key = hbox.itemAt(0).widget()
                val = hbox.itemAt(1).widget()
                key.setText(str(k))
                val.setText(str(v))
            i += 1

        # Remove any extra widgets
        while i < items_in_layout:
            item = self.vbox.takeAt(i)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
            items_in_layout -= 1


class SampleStatusBox(StatusBox):
    """
    Status box specifically for displaying sample information.

    Parameters
    ----------
    status_model : object
        Model containing status information
    title : str
        Title for the group box
    key : str
        Key to register signal with model
    parent : QWidget, optional
        Parent widget
    """

    DEFAULT_KEYS = ["name", "sample_id", "description", "position"]

    def __init__(self, status_model, title, key="GLOBAL_SELECTED", parent=None):
        super().__init__(
            status_model, title, key, display_keys=self.DEFAULT_KEYS, parent=parent
        )


class RedisStatusBox(QGroupBox):
    """
    A status box that displays metadata from a Redis dictionary.

    Parameters
    ----------
    user_status : UserStatus
        The user status model containing Redis configuration
    title : str
        Title for the group box
    topic : str
        Redis topic to subscribe to
    parent : QWidget, optional
        Parent widget
    """

    def __init__(self, user_status, title, topic="", redis_dict=None, parent=None):
        print(f"Initializing RedisStatusBox {title}")
        super().__init__(title, parent)
        self.model = user_status

        # Get Redis dict for metadata
        if redis_dict is None:
            self.redis_dict = self.model.get_redis_dict(topic)
        else:
            self.redis_dict = redis_dict
        if self.redis_dict is None:
            print(f"Warning: Redis not configured, {title} will be empty")
            return

        # Setup layout
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        print("Connecting RedisStatusBox redis_dict to update")
        # Connect to Redis changes
        self.redis_dict.changed.connect(self.update_display)

        # Initial update
        self.update_display()

    def get_display_data(self):
        """
        Get the data to display from Redis.
        Should be overridden by subclasses to format the data appropriately.

        Returns
        -------
        dict
            Dictionary of key-value pairs to display
        """
        try:
            return self.redis_dict
        except KeyError:
            return {}

    def update_display(self):
        """Update the display with current Redis data"""
        print("RedisStatusBox update display")
        # Clear existing widgets and layouts
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively clear and delete the layout
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()

        # Get and format the data
        display_data = self.get_display_data()

        # Add to layout
        for k, v in display_data.items():
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(str(k)))
            hbox.addWidget(QLabel(str(v)))
            self.vbox.addLayout(hbox)


class NewProposalDialog(QDialog):
    def __init__(self, title, run_engine):
        super().__init__()
        self.REClientModel = run_engine
        self.setWindowTitle(title)
        vbox = QVBoxLayout()
        button = QPushButton("Submit")
        button.clicked.connect(self.submit_form)
        form = QFormLayout()
        self.name = QLineEdit()
        self.SAF = QLineEdit()
        self.proposal = QLineEdit()
        self.cycle = QLineEdit()
        self.year = QLineEdit()
        form.addRow("Name", self.name)
        form.addRow("proposal", self.proposal)
        form.addRow("SAF", self.SAF)
        form.addRow("Cycle", self.cycle)
        form.addRow("Year", self.year)
        vbox.addLayout(form)
        vbox.addWidget(button)
        self.setLayout(vbox)

    def submit_form(self):
        names = self.name.text()
        proposal = int(self.proposal.text())
        saf = int(self.SAF.text())
        cycle = int(self.cycle.text())
        year = int(self.year.text())
        function = BFunc("new_proposal", names, proposal, year, cycle, saf)
        self.REClientModel._client.function_execute(function)


class ProposalStatus(QWidget):
    def __init__(self, run_engine, user_status):
        super().__init__()
        status = RedisStatusBox(user_status, "User Metadata", "USER_MD")
        self.REClientModel = run_engine

        self.button = QPushButton("New Proposal")
        self.button.clicked.connect(self.push_button)
        vbox = QVBoxLayout()
        vbox.addWidget(status)
        vbox.addWidget(self.button)
        self.setLayout(vbox)

    def push_button(self):
        dlg = NewProposalDialog("New Proposal", self.REClientModel)
        dlg.exec()


class BLController(QGroupBox):
    disableSignal = Signal()

    def __init__(self, model, *args, **kwargs):
        super().__init__("Endstation Control", *args, **kwargs)
        self.model = model
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(""))
        onbutton = QPushButton("Request Control")
        self.onValue = 4
        onbutton.showConfirmDialog = True
        onbutton.confirmMessage = "Are you sure you can have control?"
        offbutton = QPushButton("Give Up Control")
        self.offValue = 9
        offbutton.showConfirmDialog = True
        offbutton.confirmMessage = "Are you sure you want to release control?"

        vbox.addWidget(onbutton)
        vbox.addWidget(offbutton)
        self.setLayout(vbox)

    def print_disable():
        print("Disabled in SST Control")
