Standard Tabs
=============

nbs-gui organizes functionality into tabs, each providing a specific aspect of beamline control. The tabs available depend on your :doc:`../configuration` settings.

.. toctree::
   :maxdepth: 1

   queue_control
   monitor
   console
   samples

Tab Organization
-----------------

Tabs are designed to work together in a workflow:

1. **Queue Control** - Plan and execute measurements
2. **Beamline Status** - Observe real-time device states
3. **IPython Console** - Advanced control and scripting
4. **Samples** - Manage sample information

Custom Tabs
-----------

Beamlines can add custom tabs using the plugin system. See :doc:`../development/tabs` for development information.