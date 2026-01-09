Queue Control Tab
==================

The Queue Control tab is the central hub for creating, managing, and executing measurement plans. It integrates plan creation, queue management, and real-time execution monitoring.
The tab is divided into two main groups. The left panel contains the *Plan Management* tabs, and the right panel contains the *Queue Management* tabs.

.. image:: ../_static/screenshots/queue_control_overview.png
   :alt: Queue Control tab overview
   :align: center


Plan Management
---------------
   
Create and configure measurement plans using various plan widgets. The plan editor provides multiple sub-tabs that allow for plan creation, modification, and viewing

.. attention::

   Start with the Plan Widgets tab, which is the easiest to use!

.. toctree::
   :maxdepth: 1
   :hidden:

   queue/widgets
   queue/viewer
   queue/editor
   queue/loaders
   queue/metaplan

.. grid:: 1 2 3 5

   .. grid-item-card:: Plan Viewer Tab
      :link: queue/viewer
      :link-type: doc

      View the parameters of plans in the queue

   .. grid-item-card:: Plan Editor Tab
      :link: queue/editor
      :link-type: doc

      Create and modify plans directly.
      
   .. grid-item-card:: Plan Widgets Tab
      :link: queue/widgets
      :link-type: doc

      Create measurement plans using convenient graphical plan widgets.

   .. grid-item-card:: Plan Loaders Tab
      :link: queue/loaders
      :link-type: doc

      Load plans from a file.

   .. grid-item-card:: Meta Plan Widget Tab
      :link: queue/metaplan
      :link-type: doc

      Create and configure measurement plans using a meta plan widget.


Queue Management
----------------
   
Manage the execution queue and view plan history.

.. toctree::
   :maxdepth: 1
   :hidden:

   queue/queue
   queue/history
   queue/staging

.. grid:: 1 3 3 3

   .. grid-item-card:: Queue Tab
      :link: queue/queue
      :link-type: doc

      Management of the execution queue

   .. grid-item-card:: History Tab
      :link: queue/history
      :link-type: doc

      View of past plans executed

   .. grid-item-card:: Staging Tab
      :link: queue/staging
      :link-type: doc

      Staging of plans for execution

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