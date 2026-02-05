from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
    QPushButton,
    QLabel,
    QFrame,
)
from qtpy.QtCore import Signal, Slot, Qt, QTimer
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

        self.vbox = QVBoxLayout(self)
        self.vbox.addWidget(self.kernel_label)

        self.placeholder = QLabel(
            "<i>Connect to Kernel by hitting the button when the kernel status is idle</i>"
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        button_layout = QHBoxLayout()

        self.connectButton = QPushButton("Connect to Kernel")
        self.connectButton.clicked.connect(self.connect_to_kernel)
        self.connectButton.setEnabled(False)
        button_layout.addWidget(self.connectButton)

        self.reconnectButton = QPushButton("Reconnect Console")
        self.reconnectButton.clicked.connect(self.reconnect_console)
        self.reconnectButton.setEnabled(False)
        button_layout.addWidget(self.reconnectButton)

        button_layout.addStretch()
        self.vbox.addLayout(button_layout)

        self._setup_debug_panel()

        self.vbox.addWidget(self.placeholder)

        self.console = None
        self.kernel_manager = None
        self.kernel_client = None

        self.diagnostic_timer = QTimer(self)
        self.diagnostic_timer.timeout.connect(self.refresh_diagnostics)
        self.diagnostic_timer.start(10000)

    def _setup_debug_panel(self):
        """Set up the collapsible debug panel."""
        self.debug_toggle_button = QPushButton("▶ Show Debug Info")
        self.debug_toggle_button.clicked.connect(self._toggle_debug_panel)
        self.debug_toggle_button.setStyleSheet("text-align: left; padding: 5px;")
        self.vbox.addWidget(self.debug_toggle_button)

        self.debug_panel = QFrame()
        self.debug_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        debug_layout = QVBoxLayout(self.debug_panel)

        self.debug_info_label = QLabel("No diagnostic information available")
        self.debug_info_label.setWordWrap(True)
        self.debug_info_label.setTextFormat(Qt.RichText)
        debug_layout.addWidget(self.debug_info_label)

        refresh_button = QPushButton("Refresh Now")
        refresh_button.clicked.connect(self.refresh_diagnostics)
        debug_layout.addWidget(refresh_button)

        self.debug_panel.setVisible(False)
        self.vbox.addWidget(self.debug_panel)

    def _toggle_debug_panel(self):
        """Toggle visibility of the debug panel."""
        is_visible = self.debug_panel.isVisible()
        self.debug_panel.setVisible(not is_visible)
        if is_visible:
            self.debug_toggle_button.setText("▶ Show Debug Info")
        else:
            self.debug_toggle_button.setText("▼ Hide Debug Info")
            self.refresh_diagnostics()

    def _gather_diagnostics(self):
        """
        Gather diagnostic information about the kernel connection.

        Returns
        -------
        dict
            Dictionary containing diagnostic information.
        """
        diagnostics = {
            "console_exists": self.console is not None,
            "kernel_manager_exists": self.kernel_manager is not None,
            "kernel_client_exists": self.kernel_client is not None,
        }

        if self.kernel_client is not None:
            try:
                diagnostics["client_is_alive"] = self.kernel_client.is_alive()
                diagnostics["channels_running"] = self.kernel_client.channels_running

                if hasattr(self.kernel_client, 'shell_channel'):
                    diagnostics["shell_channel_alive"] = self.kernel_client.shell_channel.is_alive()
                if hasattr(self.kernel_client, 'iopub_channel'):
                    diagnostics["iopub_channel_alive"] = self.kernel_client.iopub_channel.is_alive()
                if hasattr(self.kernel_client, 'stdin_channel'):
                    diagnostics["stdin_channel_alive"] = self.kernel_client.stdin_channel.is_alive()
                if hasattr(self.kernel_client, 'hb_channel'):
                    diagnostics["hb_channel_alive"] = self.kernel_client.hb_channel.is_alive()
                    if hasattr(self.kernel_client.hb_channel, 'is_beating'):
                        diagnostics["hb_is_beating"] = self.kernel_client.hb_channel.is_beating()
            except Exception as e:
                diagnostics["error"] = str(e)

        return diagnostics

    def _format_diagnostics(self, diagnostics):
        """
        Format diagnostics dictionary as HTML for display.

        Parameters
        ----------
        diagnostics : dict
            Dictionary of diagnostic information.

        Returns
        -------
        str
            HTML formatted string.
        """
        def status_color(value):
            if value is True:
                return '<span style="color: green;">✓ True</span>'
            elif value is False:
                return '<span style="color: red;">✗ False</span>'
            else:
                return f'<span style="color: orange;">{value}</span>'

        lines = ["<b>Connection Diagnostics:</b><br>"]

        lines.append(f"Console Widget: {status_color(diagnostics.get('console_exists'))}<br>")
        lines.append(f"Kernel Manager: {status_color(diagnostics.get('kernel_manager_exists'))}<br>")
        lines.append(f"Kernel Client: {status_color(diagnostics.get('kernel_client_exists'))}<br>")

        if diagnostics.get('kernel_client_exists'):
            lines.append("<br><b>Client Status:</b><br>")
            lines.append(f"Client Alive: {status_color(diagnostics.get('client_is_alive'))}<br>")
            lines.append(f"Channels Running: {status_color(diagnostics.get('channels_running'))}<br>")

            lines.append("<br><b>Channel Status:</b><br>")
            lines.append(f"Shell Channel: {status_color(diagnostics.get('shell_channel_alive', 'N/A'))}<br>")
            lines.append(f"IOPub Channel: {status_color(diagnostics.get('iopub_channel_alive', 'N/A'))}<br>")
            lines.append(f"Stdin Channel: {status_color(diagnostics.get('stdin_channel_alive', 'N/A'))}<br>")
            lines.append(f"Heartbeat Channel: {status_color(diagnostics.get('hb_channel_alive', 'N/A'))}<br>")

            if 'hb_is_beating' in diagnostics:
                lines.append(f"Heartbeat Beating: {status_color(diagnostics.get('hb_is_beating'))}<br>")

        if 'error' in diagnostics:
            lines.append(f"<br><b>Error:</b> <span style='color: red;'>{diagnostics['error']}</span><br>")

        return "".join(lines)

    @Slot()
    def refresh_diagnostics(self):
        """Refresh the diagnostic information display."""
        diagnostics = self._gather_diagnostics()
        formatted = self._format_diagnostics(diagnostics)
        self.debug_info_label.setText(formatted)

    def reconnect_console(self):
        """Fully recreate the console widget and reconnect to the kernel."""
        self._cleanup_console()
        self.connect_to_kernel()

    def _cleanup_console(self):
        """Clean up the existing console widget and connections."""
        if self.kernel_client is not None:
            try:
                if self.kernel_client.channels_running:
                    self.kernel_client.stop_channels()
            except Exception:
                pass
            self.kernel_client = None

        if self.kernel_manager is not None:
            self.kernel_manager = None

        if self.console is not None:
            try:
                self.console.kernel_client = None
                self.console.kernel_manager = None
            except Exception:
                pass
            self.vbox.removeWidget(self.console)
            self.console.deleteLater()
            self.console = None

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

        if kernel_state in ["idle", "busy"] and self.console is not None:
            self.reconnectButton.setEnabled(True)
        else:
            self.reconnectButton.setEnabled(False)

    def connect_to_kernel(self):
        """
        Connect to the IPython kernel when the button is pressed.

        Cleans up any existing console widget and creates a fresh connection.
        """
        print("Connecting to Kernel")

        self._cleanup_console()

        if self.placeholder is not None:
            self.vbox.removeWidget(self.placeholder)
            self.placeholder.hide()

        self.console = RichJupyterWidget()
        self.console.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.vbox.addWidget(self.console)

        msg = self.REClientModel._client.config_get()
        connect_info = msg["config"]["ip_connect_info"]

        self.kernel_manager = QtKernelManager()
        self.kernel_manager.load_connection_info(connect_info)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        self.console.kernel_manager = self.kernel_manager
        self.console.kernel_client = self.kernel_client
        print("Done connecting to Kernel")

        self.refresh_diagnostics()

    def is_console_connected(self):
        if (
            self.console is not None
            and self.console.kernel_client
            and self.console.kernel_client.is_alive()
        ):
            return True
        return False
