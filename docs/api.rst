API Reference
=============

This section contains the complete API reference for the NBS-GUI framework. All classes, functions, and modules are documented with their parameters, return values, and usage examples.

.. toctree::
   :maxdepth: 3
   :caption: API Contents

Core Framework
--------------

Main Module
~~~~~~~~~~~

.. automodule:: nbs_gui
   :members:
   :undoc-members:
   :show-inheritance:

Settings and Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: nbs_gui.settings
   :members:
   :undoc-members:
   :show-inheritance:

Model Layer
-----------

Base Models
~~~~~~~~~~~

Core model functionality and base classes.


Device Models
~~~~~~~~~~~~~

Models for specific device types.

Motor Models
^^^^^^^^^^^^

Base Motor Classes
""""""""""""""""""

.. autoclass:: nbs_gui.models.motors.BaseMotorModel
   :members:
   :undoc-members:
   :show-inheritance:

EPICS Motor Model
"""""""""""""""""

.. autoclass:: nbs_gui.models.motors.EPICSMotorModel
   :members:
   :undoc-members:
   :show-inheritance:

PV Positioner Model
"""""""""""""""""""

.. autoclass:: nbs_gui.models.motors.PVPositionerModel
   :members:
   :undoc-members:
   :show-inheritance:

Other Device Models
^^^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.models.misc
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.models.mode
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.models.redis
   :members:
   :undoc-members:
   :show-inheritance:

View Layer
----------

Base Views
~~~~~~~~~~

Core view functionality.

Device Views
~~~~~~~~~~~~

Views for specific device types.

Motor Views
^^^^^^^^^^^

Motor Monitor
"""""""""""""

.. autoclass:: nbs_gui.views.motor.MotorMonitor
   :members:
   :undoc-members:
   :show-inheritance:

Motor Control
"""""""""""""

.. autoclass:: nbs_gui.views.motor.MotorControl
   :members:
   :undoc-members:
   :show-inheritance:

Other Device Views
^^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.views.monitors
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.views.status
   :members:
   :undoc-members:
   :show-inheritance:

Widget Components
-----------------

Plan Widgets
~~~~~~~~~~~~

Plan Base Classes
^^^^^^^^^^^^^^^^^

Auto Plan Widget
""""""""""""""""

.. autoclass:: nbs_gui.plans.base.AutoPlanWidget
   :members:
   :undoc-members:
   :show-inheritance:

NBS Plan Base
"""""""""""""

.. autoclass:: nbs_gui.plans.nbsPlan.NBSPlanWidget
   :members:
   :undoc-members:
   :show-inheritance:

Built-in Plan Widgets
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.plans.scanPlan
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.plans.movePlan
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.plans.xasPlan
   :members:
   :undoc-members:
   :show-inheritance:

UI Widgets
~~~~~~~~~~

Queue Control Widgets
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.widgets.planSubmission
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.widgets.planEditor
   :members:
   :undoc-members:
   :show-inheritance:

Tab Components
--------------

Standard Tabs
~~~~~~~~~~~~~

Queue Control Tab
^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.tabs.queueControlTab
   :members:
   :undoc-members:
   :show-inheritance:

Motor Tab
^^^^^^^^^

.. automodule:: nbs_gui.tabs.motorTab
   :members:
   :undoc-members:
   :show-inheritance:

Other Standard Tabs
^^^^^^^^^^^^^^^^^^^

.. automodule:: nbs_gui.tabs.sampleTab
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.tabs.consoleTab
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: nbs_gui.tabs.monitorTab
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

Qt Helpers
~~~~~~~~~~

.. automodule:: nbs_gui.utils.qt_helpers
   :members:
   :undoc-members:
   :show-inheritance:

Loading and Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: nbs_gui.load
   :members:
   :undoc-members:
   :show-inheritance:

Main Application
~~~~~~~~~~~~~~~~

.. automodule:: nbs_gui.main
   :members:
   :undoc-members:
   :show-inheritance: