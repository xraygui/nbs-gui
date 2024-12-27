from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QPushButton,
    QLabel,
)
from qtpy.QtCore import Signal, Slot, Qt
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

# from bluesky_widgets.qt.ipython_console import QtReIPythonConsole

# import sys
# import argparse
# import subprocess
# import os


# def get_jupyter_runtime_dir():
#     """Get the Jupyter runtime directory."""
#     return subprocess.check_output(["jupyter", "--runtime-dir"]).decode("utf-8").strip()


class NewIPythonConsoleTab(QWidget):
    name = "New IPython Console"

    def __init__(self, model, *args, **kwargs):
        print("Initializing IPythonConsoleTab")
        super().__init__(*args, **kwargs)
        vbox = QVBoxLayout()
        print("Creating Ipython widget")
        self.ipython_widget = QtReIPythonConsole(model.run_engine)
        vbox.addWidget(self.ipython_widget)
        self.setLayout(vbox)


class IPythonConsoleTab(QWidget):
    """
    A QWidget that contains an embedded IPython console.

    Attributes
    ----------
    console : RichJupyterWidget
        The embedded IPython console widget.
    kernel_manager : QtKernelManager
        Manager for the IPython kernel.
    kernel_client : QtKernelClient
        Client for interacting with the kernel.
    """

    name = "IPython Console"
    signal_update_widget = Signal(object)

    def __init__(self, model):
        """
        Initialize the IPython console tab.

        Parameters
        ----------
        model : bluesky_widgets.models.run_engine.RERunEngine
            Run engine model that provides kernel connection status and control
        """
        super().__init__()
        self.kernel_label = QLabel("Kernel Status: Not Connected")
        self.REClientModel = model.run_engine
        self.REClientModel.events.status_changed.connect(self.on_update_widgets)
        self.signal_update_widget.connect(self.slot_update_widgets)

        # Create main layout
        self.vbox = QVBoxLayout(self)
        self.vbox.addWidget(self.kernel_label)

        # Create placeholder widget
        self.placeholder = QLabel(
            "<i>Connect to Kernel by hitting the button when the kernel status is idle</i>"
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add placeholder to layout

        # Create connect button
        self.connectButton = QPushButton("Connect to Kernel")
        self.connectButton.clicked.connect(self.connect_to_kernel)
        self.connectButton.setEnabled(False)

        self.vbox.addWidget(self.connectButton)
        # self.vbox.addWidget(QtReStatusMonitor(self.REClientModel))
        self.vbox.addWidget(self.placeholder)

        # Initialize console reference as None
        self.console = None
        self.kernel_manager = None
        self.kernel_client = None

    def on_update_widgets(self, event):
        status = event.status
        self.signal_update_widget.emit(status)

    @Slot(object)
    def slot_update_widgets(self, status):
        kernel_state = status.get("ip_kernel_state", None)
        if kernel_state is not None:
            self.kernel_label.setText(f"Kernel State: {kernel_state}")
        else:
            self.kernel_label.setText("Kernel State: Not Connected")
        if kernel_state in ["idle", "busy"] and not self.is_console_connected():
            self.connectButton.setEnabled(True)
        else:
            self.connectButton.setEnabled(False)

    def connect_to_kernel(self):
        """
        Connects to the IPython kernel when the button is pressed.
        Prioritizes the file path from the QLineEdit if provided.
        """
        print("Connecting to Kernel")

        # Clean up existing console if it exists
        if self.console is not None:
            self.console.kernel_client.stop_channels()
            self.console.kernel_manager = None
            self.console.kernel_client = None
            self.vbox.removeWidget(self.console)
            self.console.deleteLater()
            self.console = None

        # Remove placeholder if it exists
        if self.placeholder is not None:
            self.vbox.removeWidget(self.placeholder)
            self.placeholder.hide()

        # Create new console widget
        self.console = RichJupyterWidget()
        self.console.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Insert console widget after kernel label but before buttons
        self.vbox.addWidget(self.console)

        # Setup kernel connection
        msg = self.REClientModel._client.config_get()
        connect_info = msg["config"]["ip_connect_info"]

        self.kernel_manager = QtKernelManager()
        self.kernel_manager.load_connection_info(connect_info)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        # Connect the console widget to the kernel
        self.console.kernel_manager = self.kernel_manager
        self.console.kernel_client = self.kernel_client
        print("Done connecting to Kernel")

    def is_console_connected(self):
        if (
            self.console is not None
            and self.console.kernel_client
            and self.console.kernel_client.is_alive()
        ):
            return True
        return False
