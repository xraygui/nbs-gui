GUI Mode Management
====================

Overview
--------

The GUI supports beamlines that can operate in different modes (e.g., tender/soft X-rays), where certain devices and widgets should only be available in specific modes. The system should also work seamlessly for beamlines without modes.

Configuration 
--------------

devices.toml
~~~~~~~~~~~~

The beamline configuration file (devices.toml) should contain a section for the mode device. This example defines a mode device backed by a Redis database, but it is possible to use any EPICS PV as well.

  .. code-block:: toml

     [mode]
     _target = "nbs_bl.redisDevice.RedisModeDevice"
     prefix = "MODE_STATE"
     name = "mode"
     _role = "mode"
     _group = "signals"

gui_config.toml
~~~~~~~~~~~~~~~

The mode device target needs to be added to the GUI configuration file

  .. code-block:: toml
    
      [loaders]
      "RedisModeDevice" = "nbs_gui.models.mode.RedisModeModel"


This ensures that the mode device is loaded and available in the GUI. The GUI will automatically listen for mode changes, and update the device availability accordingly.

Switching modes
---------------

* If a GUI model is chosen that has read-write permissions, it will be possible to switch the beamline mode from the GUI
