Plan Viewer Tab
---------------

.. card::

    .. image:: ../../_static/screenshots/plan_viewer_widget.png
      :alt: Plan viewer widget

The Plan Viewer tab shows the details of a plan that has been selected in the queue, including the parameters and the metadata.
Unlike the user-friendly Plan Widgets view, the Plan Viewer shows the raw parameters that will be sent to the QueueServer, and
makes no distinction between different plan types.

Unlike the compact view in the Plan Queue, the Plan Viewer also shows possible keyword arguments for the plan, which have not been passed a value.

The Plan Viewer is most useful for examining possible errors in a plan before it is run, and triggering the **Plan Editor** via the "Edit" button 