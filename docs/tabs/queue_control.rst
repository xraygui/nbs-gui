Queue Control Tab
==================

The Queue Control tab is the central hub for creating, managing, and executing measurement plans. It integrates plan creation, queue management, and real-time execution monitoring.

.. image:: ../_static/screenshots/queue_control_overview.png
   :alt: Queue Control tab overview
   :align: center

The tab is divided into two main groups. The left panel contains the *Plan Management* tabs, and the right panel contains the *Queue Management* tabs.

Plan Management
---------------
   
Create and configure measurement plans using various plan widgets. The plan editor provides multiple sub-tabs that allow for plan creation, modification, and viewing

.. toctree::
   :maxdepth: 1

   queue/widgets
   queue/viewer
   queue/editor
   queue/loaders
   queue/metaplan

Queue Management
----------------
   
Manage the execution queue and view plan history.

.. toctree::
   :maxdepth: 1

   queue/queue
   queue/history
   queue/staging

QueueServer Log
---------------

The QueueServer log, at the very bottom of the tab, provides output from the QueueServer process. 
This is useful for debugging issues, especially on QueueServer startup, or when plans are not adding or executing.


Common Workflows
----------------
Plan Modification
~~~~~~~~~~~~~~~~~

1. Create base plan in Plan Editor
2. Stage in Queue Staging
3. Double-click to edit parameters
4. Modify settings as needed
5. Add to Plan Queue

Troubleshooting
---------------

**Plans not executing**
   Check queue server connection and device status.

**Plan creation errors**
   Verify all required parameters are set and devices are available.

**Queue stuck**
   Use the stop button and clear problematic plans.

See Also
--------

* :doc:`../workflows` - Complete workflow examples
* :doc:`../development/plans` - Creating custom plan widgets
* :doc:`../configuration` - Configuring available plan types