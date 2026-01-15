Standard Tabs
=============

nbs-gui organizes functionality into tabs, each providing a specific aspect of beamline control. 
The tabs available depend on your :doc:`../configuration` settings. Each standard tab is described in the links below.

.. toctree::
   :maxdepth: 1
   :hidden:

   queue_control
   monitor
   console
   samples

.. grid:: 1 2 4 4

   .. grid-item-card:: Queue Control Tab
      :link: queue_control
      :link-type: doc

      Plan and execute measurements

   .. grid-item-card:: Monitor Tab
      :link: monitor
      :link-type: doc

      Observe real-time device states

   .. grid-item-card:: Console Tab
      :link: console
      :link-type: doc

      Advanced control and scripting

   .. grid-item-card:: Samples Tab
      :link: samples
      :link-type: doc

      Manage sample information


Custom Tabs
-----------

Beamlines can add custom tabs using the plugin system. See :doc:`../development/tabs` for development information.