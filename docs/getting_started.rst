Getting Started
===============

Welcome to nbs-gui, the NSLS-II Beamline GUI Framework! This guide will help you get up and running quickly.

Installation
------------

Prerequisites
~~~~~~~~~~~~~

nbs-gui requires:

* **Python 3.8+**
* **Qt** (via qtpy - supports PyQt5, PyQt6, PySide2, or PySide6)
* **Redis** for device state management
* **Bluesky** and **Ophyd** for beamline control
* **Bluesky Queue Server** running (see nbs-bl documentation)

Installing from Source
~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/xraygui/nbs-gui.git
   cd nbs-gui
   pip install -e .

For beamline development, you may also need:

.. code-block:: bash

   pip install nbs-bl  # Beamline support library
   pip install nbs-core  # Core utilities

Alternatively, if you have pixi installed, you can use the pixi environment which automatically includes all dependencies including Qt:

.. code-block:: bash

   cd nbs-gui
   pixi install  # Install all dependencies
   pixi shell    # Activate the environment

First-Time Setup
----------------

Configuration Files
~~~~~~~~~~~~~~~~~~~

nbs-gui requires two main configuration files:

1. **devices.toml** - Defines your beamline's Ophyd devices (see nbs-bl documentation for setup)
2. **gui_config.toml** - Configures the GUI appearance and behavior

For this tutorial, we assume you have already set up a ``devices.toml`` file in an IPython profile called "collection". See the nbs-bl documentation for detailed instructions on creating and configuring your ``devices.toml`` file.

Example minimal gui_config.toml:

.. code-block:: toml

   [gui]
   header = "nbs-gui-header"

   [gui.tabs]
   include = ["nbs-gui-queue", "nbs-gui-console", "nbs-gui-monitor"]

   [gui.plans]
   include = ["nbs-gui-scan", "nbs-gui-move"]

   [loaders]
   "EpicsSignalRO" = "nbs_gui.models.PVModel"
   "EpicsSignal" = "nbs_gui.models.PVModel"
   "EpicsMotor" = "nbs_gui.models.MotorModel"



See the :doc:`configuration` guide for complete configuration options.

Launching the GUI
-----------------

Launch nbs-gui from the command line. We recommend using pixi to ensure all dependencies (including Qt) are properly installed:

.. code-block:: bash

   pixi run nbs-gui --profile collection

If you prefer to use the direct command (ensure Qt is installed on your system):

.. code-block:: bash

   nbs-gui --profile collection

The ``--profile`` flag specifies which IPython profile to use (in this case, "collection" where your devices.toml and gui_config.toml are located).

For minimal interface (useful for testing, does not load any devices):

.. code-block:: bash

   pixi run nbs-minimal-gui



Quick Tour of the Interface
---------------------------

When you first launch nbs-gui, you'll see:

**Header Bar**
   At the top of the window, shows connection status and provides quick access to common functions.

**Tab Area**
   Below the header, tabs organize different aspects of beamline control, for example:

   * **Queue Control** - Create and manage measurement plans
   * **Console** - Interactive Python/IPython terminal
   * **Monitor** - Real-time display of device states

Connecting to the QueueServer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Assuming a QueueServer is running, you can connect to it by clicking the "Connect" button in the Queue Server controls widget in the header bar.
* If the QueueServer does not have a worker environment, you can open it by clicking the "Open" button.
* Output from the worker startup will be displayed in the terminal output of the Queue Control tab.
* The QueueServer controls widget will update to reflect the connection status, RunEngine status, and other information.

Basic Workflow
--------------

A typical measurement workflow:

1. **Configure your beamline** - Set up devices in devices.toml (see nbs-bl documentation)
2. **Start Queue Server** - Ensure a Bluesky Queue Server is running (see nbs-bl documentation)
3. **Launch the GUI** - Start nbs-gui with your profile
4. **Check connections** - Verify QueueServer is connected and running
5. **Create a plan** - Use the Queue Control tab to set up measurements
6. **Execute** - Run the plan and monitor progress
7. **Review results** - Check the plan history and any output files

Next Steps
----------

* Learn about :doc:`configuration` options
* Explore the standard :doc:`tabs/index`
* See common :doc:`workflows` for detailed examples
* For development, check the :doc:`../architecture` guide