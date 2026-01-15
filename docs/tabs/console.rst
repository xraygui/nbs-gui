Console Tab
===========

The Console tab provides an interactive IPython terminal for advanced beamline control, scripting, and debugging. 
It offers full access to the Bluesky and Ophyd APIs for programmatic control.

.. card::
   
   .. image:: ../_static/screenshots/console_overview.png
      :alt: IPython console interface
      :align: center


Common Tasks
------------

Device Inspection
~~~~~~~~~~~~~~~~~

The iPython console can be used to inspect the state of devices, usually for debugging purposes.

.. card::

   .. image:: ../_static/screenshots/console_device_inspection.png

Plan Creation
~~~~~~~~~~~~~

New plans can be created in the console by defining a function with ``yield`` statements, just as from a normal
Bluesky terminal. These functions can then be run through the RunEngine, using ``RE(...)`` as normal.

.. card::

   .. image:: ../_static/screenshots/console_def_and_run.png


Script Development
~~~~~~~~~~~~~~~~~~

Scripts can be loaded with the ipython magic command ``%run``. This can be useful to develop longer scripts in 
a text editor, or run previously saved scripts.

.. code-block:: python

   # Run script
   %run my_script.py

Debugging
-----------

.. card::

   .. image:: ../_static/screenshots/console_error.png
      :alt: Error in script
      :align: center

If you cannot get a plan to work in the QueueServer, try running it in the console. The error messages are more
detailed, and there is the ``%tb verbose`` option to see a full stack trace. It is recommended to test all user-defined
plans in this way before submitting to a queue.

.. attention::

   Bluesky is notorious for having extremely long error tracebacks. Usually, the relevant portion of the traceback will
   be either at the very beginning, or at the very end. The middle typically consists of a lot of irrelevant redirects, as the
   error works its way through the deeply nested functions that Bluesky uses to implement its features.

See Also
--------

* :doc:`../workflows` - Advanced scripting examples
* `Bluesky Documentation <https://blueskyproject.io/bluesky/>`_ - Bluesky plan reference
* `Ophyd Documentation <https://blueskyproject.io/ophyd/>`_ - Device control reference
* `IPython Documentation <https://ipython.readthedocs.io/>`_ - Console features