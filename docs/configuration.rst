Configuration
=============

nbs-gui is configured using TOML configuration files. The main configuration file is typically called ``gui_config.toml`` and should be placed in your IPython profile's startup directory.

File Location
-------------

Configuration files are loaded from the selected IPython profile's startup directory. I.e, for a typical ipython installation, with a profile called "collection", the configuration files will be loaded from ``~/.ipython/profile_collection/startup/``.

Configuration Sections
----------------------

gui
~~~~~

Controls the overall GUI appearance and layout.

**header** (string)
   Entry point name for the header widget. Default: ``"nbs-gui-header"``

   Available options:

   * ``"nbs-gui-header"`` - Standard header with connection status, motor status indicators, and running plan display
   * ``"nbs-gui-minimal-header"`` - Minimal header for testing with no motor status indicators

.. code-block:: toml

   [gui]
   header = "nbs-gui-header"

gui.tabs
~~~~~~~~~~~

Controls which tabs are displayed in the main tab bar.

**include** (array of strings)
   List of entry point names for tabs to include. If include is provided, only listed tabs will be shown.

   Available standard tabs:

   * ``"nbs-gui-queue"`` - Queue Control tab
   * ``"nbs-gui-motors"`` - Motor control tab
   * ``"nbs-gui-samples"`` - Sample management tab
   * ``"nbs-gui-console"`` - IPython console tab
   * ``"nbs-gui-monitor"`` - Device monitor tab
   * ``"kafka-table-tab"`` - Kafka data table viewer tab (from livetable package)

**exclude** (array of strings)
   List of entry point names for tabs to exclude. If exclude is provided, the listed tabs will not be shown, but all others will be shown.

.. code-block:: toml

   [gui.tabs]
   include = ["nbs-gui-queue", "nbs-gui-motors", "nbs-gui-console"]

If include is provided, any values for exclude will be ignored. Tab names correspond to the "nbs-gui.tabs" entrypoint group. If include is not provided, all tabs will be shown except for those listed in exclude.

gui.plans
~~~~~~~~~~~

Controls which plan widgets are available in the plan editor.

**include** (array of strings)
   List of entry point names for plan widgets to include.

   Available standard plans:

   * ``"nbs-gui-scan"`` - Basic scanning plans
   * ``"nbs-gui-move"`` - Motor movement plans
   * ``"nbs-gui-xas"`` - X-ray absorption spectroscopy plans
   * ``"nbs-gui-timescan"`` - Time-based scanning
   * ``"nbs-gui-varscan"`` - Variable step scanning
   * ``"nbs-gui-flyscan"`` - Fly scanning plans
   * ``"nbs-gui-samplemove"`` - Sample positioning plans

**exclude** (array of strings)
   List of entry point names for plan widgets to exclude. If exclude is provided, the listed plan widgets will not be shown, but all others will be shown.

.. code-block:: toml

   [gui.plans]
   include = ["nbs-gui-scan", "nbs-gui-move", "nbs-gui-xas"]

If include is provided, any values for exclude will be ignored. Plan widget names correspond to the "nbs_gui.plans" entrypoint group. If include is not provided, all plan widgets will be shown except for those listed in exclude.

models.beamline
~~~~~~~~~~~~~~~~~

Configures beamline-specific models and their primary devices. Some special devices are placed in more prominent locations in the GUI.

**primary_energy** (string)
   Name of the primary energy device for energy-related calculations.

**primary_manipulator** (string)
   Name of the primary sample manipulator device.

**loader** (string, optional)
   Entry point name for a custom beamline model class.

.. code-block:: toml

   [models.beamline]
   primary_energy = "en"
   primary_manipulator = "manipulator"
   loader = "nbs_bl.qt.models.beamline.SSTBeamlineModel"

devices
~~~~~~~~~

Configures individual device behavior and appearance.

Each key should correspond to a device name in your ``devices.toml`` file. The following options are available:

**visible** (boolean, optional)
   Whether the device appears in the GUI. Default: ``true``

**view_only** (boolean, optional)
   Whether the device is read-only (no controls). Default: ``false``

**label** (string, optional)
   Custom display name for the device.

**_role** (string, optional)
   Overrides the role of the device as defined in your ``devices.toml`` file. This is mainly useful for cases when an aliased device has a role, but the GUI needs to use the top-level device.

**load_order** (integer, optional)
   Order in which devices are initialized (lower numbers first).

**_group** (string, optional)
   Overrides the group of the device as defined in your ``devices.toml`` file. This is mainly useful for cases when a device belongs to more than one group in devices.toml, but should only be displayed in one group in the GUI.

.. code-block:: toml

   [devices]
   # Hide beamline shutters from main interface
   psh1 = { visible = false, view_only = true }
   psh4 = { visible = false }

   # Configure energy device
   en = { "_role" = "energy", "load_order" = 1 }

   # Custom label for exit slit
   Exit_Slit = { label = "Exit Slit" }

loaders
~~~~~~~~~

Maps Ophyd device classes to Qt model classes. This is used to instantiate the GUI models for the devices.

Each entry maps an Ophyd class name to a model loader entry point. Each key should correspond to a class name from the _target field of a device in your devices.toml file.

Devices which do not have a corresponding loader entry will not be loaded at all in the GUI. 

Common mappings:

.. code-block:: toml

   [loaders]
   # Motor models
   "EpicsMotor" = "nbs_gui.models.MotorModel"

   # Signal models
   "EpicsSignal" = "nbs_gui.models.PVModel"
   "EpicsSignalRO" = "nbs_gui.models.PVModel"

   # Gate valve models
   "ShutterSet" = "nbs_gui.models.GVModel"
   "EPS_Shutter" = "nbs_gui.models.GVModel"

   # Complex devices
   "ManipulatorBuilder" = "nbs_gui.models.PseudoPositionerModel"
   "FMBHexapodMirror" = "nbs_gui.models.MotorTupleModel"

   # Mode management
   "RedisModeDevice" = "nbs_gui.models.mode.RedisModeModel"

kafka
~~~~~~~

Optional Kafka integration for data streaming.

**config_file** (string)
   Path to Kafka configuration file.

**bl_acronym** (string)
   Beamline acronym for Kafka topics.

.. code-block:: toml

   [kafka]
   config_file = "/etc/bluesky/kafka.yml"
   bl_acronym = "nbs"

Complete Example
----------------

Here's a complete example configuration:

.. code-block:: toml

   [gui]
   header = "nbs-gui-header"

   [gui.tabs]
   include = ["nbs-gui-queue", "nbs-gui-motors", "nbs-gui-samples", "nbs-gui-console", "nbs-gui-monitor"]

   [gui.plans]
   include = [
       "nbs-gui-scan",
       "nbs-gui-move",
       "nbs-gui-xas",
       "nbs-gui-timescan",
       "nbs-gui-varscan",
       "nbs-gui-flyscan",
       "nbs-gui-samplemove"
   ]

   [models.beamline]
   primary_energy = "en"
   primary_manipulator = "manipulator"
   loader = "nbs_bl.qt.models.beamline.SSTBeamlineModel"

   [devices]
   # Hide beamline shutters
   psh1 = { visible = false, view_only = true }
   psh4 = { visible = false }

   # Configure energy device
   en = { "_role" = "energy", "load_order" = 1 }

   # Custom labels
   Exit_Slit = { label = "Exit Slit" }
   tes = { "_group" = "misc" }

   [loaders]
   "EnPosFactory" = "nbs_bl.qt.models.energy.SST1EnergyModel"
   "I400SingleCh" = "nbs_gui.models.ScalarModel"
   "PrettyMotorFMBO" = "nbs_gui.models.MotorModel"
   "PrettyMotor" = "nbs_gui.models.MotorModel"
   "EpicsSignalRO" = "nbs_gui.models.PVModel"
   "EpicsSignal" = "nbs_gui.models.PVModel"
   "ShutterSet" = "nbs_gui.models.GVModel"
   "EPS_Shutter" = "nbs_gui.models.GVModel"
   "ManipulatorBuilder" = "nbs_gui.models.PseudoPositionerModel"
   "ophScalar" = "nbs_gui.models.ScalarModel"
   "ADCBuffer" = "nbs_gui.models.ScalarModel"
   "SRSADCFactory" = "nbs_base.qt.models.srs570.SRS570Model"
   "RBD9103Factory" = "nbs_base.qt.models.rbd9103.RBD9103Model"
   "TESMCAFactory" = "ucal.qt.models.tesModel.TESModel"
   "WienerPSFactory" = "nbs_gui.models.MotorTupleModel"
   "Fasstcat" = "sst_fasstcat.qt.models.fasstcat.FasstcatModel"
   "RedisModeDevice" = "nbs_gui.models.mode.RedisModeModel"

   [kafka]
   config_file = "/etc/bluesky/kafka.yml"
   bl_acronym = "nbs"

See Also
--------

* :doc:`mode_management` - Using mode-based device management
* :doc:`../development/plugins` - Creating custom components
* :doc:`../api` - Complete API reference for configuration options