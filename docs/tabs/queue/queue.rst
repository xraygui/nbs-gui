Plan Queue Tab 
--------------

.. card::

   .. image:: ../../_static/screenshots/queue_area_overview.png
      :alt: Plan Queue tab
      :align: center

The Plan Queue tab shows plans waiting to be executed. The bulk of the tab is devoted to the list of plans, with
their parameters displayed in a table. Some plans may have a time estimate, based on the number of steps and the dwell time.

.. note::

    The plan name and parameters may differ from the display names in the Plan Widgets. These are the "raw" names
    that actually get passed to the QueueServer and executed in Python.

A button bar at the top provides some basic manipulation options for the queue.

Up:
  Move the selected plan(s) up by one position.
Down:
  Move the selected plan(s) down by one position.
Top:
  Move the selected plan(s) to the top of the queue.
Bottom:
  Move the selected plan(s) to the bottom of the queue.
Deselect:
  Deselect all plans.
Clear:
  Clear the queue.
Loop:
  Toggle loop mode on/off.
Delete:
  Delete the selected plan.
Duplicate:
  Duplicate the selected plan.

Queue Execution
~~~~~~~~~~~~~~~~~~

Queue execution is controlled by the always-visible header boxes

.. card::

    .. image:: ../../_static/screenshots/queue_header_cluster.png
        :alt: Queue header boxes
        :align: center

Plans may be executed in one of three ways:

Start:
    Hitting the "Start" button will execute all plans in the queue, in order.
Execute One Plan:
    Hitting the "Execute One Plan" button will execute the next plan in the queue, and then stop
Auto:
    If the "Auto" checkbox is checked, the queue will execute plans automatically when they are added to the queue.

.. attention::

    When the queue is started, the "Start" button will change to "Stop". Clicking "Stop" will halt further queue execution,
    but will not affect the plan that is currently executing.

Pausing A Running Plan
~~~~~~~~~~~~~~~~~~~~~~

Sometimes it will be necessary to pause the queue. Most commonly, to allow the user to manually intervene with a motor,
or as a precursor to cancelling a plan. When a plan is running, the "Pause" button will be enabled.

.. card::

    .. image:: ../../_static/screenshots/plan_pause_prep.png
        :alt: Queue running
        :align: center

    .. image:: ../../_static/screenshots/plan_paused.png
        :alt: Queue paused
        :align: center

Clicking "Pause" will pause the queue at the next step. The plan will be marked as "Paused" in the RUNNING PLAN box,
and the "Pause" button will change to "Resume" and "Abort".

.. attention::

    In some cases, it may be necessary to use the "Pause Immediate" button to pause the queue. This is accessible from
    the "More" dropdown menu. However, try to exercise some patience with "Pause", which will usually work if you wait
    for the next step of the plan.

Clicking "Resume" will resume the queue from the paused state, and the "Resume" button will change back to "Pause".

Cancelling A Running Plan
~~~~~~~~~~~~~~~~~~~~~~~~~

Plans can only be cancelled from a paused state. After a plan is paused, hit "Abort" to halt the plan. The
plan metadata will record that the plan did not complete successfully, allowing incomplete plans to be filtered
from later data analysis.

.. danger::
    In rare, but more-common-than-desired cases, a plan may get stuck, and cannot be halted or resumed. In this case,
    the only recourse may be the "destroy" button, which will forcefully terminate the QueueServer environment. The 
    QueueServer will need to be re-opened, and the plan will need to be re-run.