Plan Editor Tab
---------------

Overview of the Plan Editor Tab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A "direct" interface for creating and editing plans. It will be instructive to first compare to the Plan Widgets tab.

The "Movement" plan in the Plan Widgets tab is shown below. The interface is simple, and contains a drop-down menu
for the motor selection, and a named input field for the position, which has a "float" type, and will not allow incorrect input, i.e, strings.

.. card::

    .. image:: /_static/screenshots/move_plan_widget.png
        :alt: Move plan widget


The same plan in the Plan Editor tab is shown below. The interface is more complex, and contains a table of parameters, which is automatically generated from the plan signature.
There is no guidance or validation for the input, so the user must very carefully enter exactly the motor name desired, and then the position, as a list of arguments.

.. card::

    .. image:: /_static/screenshots/move_plan_editor.png
        :alt: Move plan editor

Running a Plan
~~~~~~~~~~~~~~

.. card::

    .. image:: /_static/screenshots/plan_editor_overview.png
        :alt: Plan editor overview

The Plan Editor tab is divided into a plan selection bar, and the parameter table. The plan selection drop-down contains
all selectable plans, organized into four Categories

Scan
    A curated list of plans designated as "scans", which includes all of the standard plans, such as typical step scans, grid scans, etc.

Plan
    A curated list of plans that are not scans, for example, sample move plans, open/close shutters, etc.

All Plans
    A list of every single plan that is available in the QueueServer. Mostly useful for custom plans.

Instruction
    Built-in QueueServer instructions. The only current example is ``queue_stop``, which will halt the queue after execution.

.. Note::
    Be very careful editing plans! There is very little validation on the input. Some helpful tips:

    - Lists of arguments must be constructed with ``[`` and ``]`` delimiters
    - Strings must be enclosed in quotes
    - Motor and detector names must be enclosed in quotes. QueueServer will auto-resolve them to their device objects
    - True and False must be entered without quotes. Literally, ``True`` and ``False``

    There is no explanation given for any parameter, so it will be most helpful to refer to documentation for Bluesky,
    or the source code for the plan. It may also be helpful to run the plan in the Console tab first, to get immediate
    feedback on the arguments.

.. Danger::
    Due to the automatic generation of the All Plans list, there are many plans that are not sensible to run.
    For example, "declare_stream" is a plan stub, which will not run correctly by itself, and should never be run by hand.
    "install_suspender" takes a function as an argument, which cannot be passed as a string. Only try to run plans from the All Plans list
    if you are absolutely sure you know what the plan does, and what arguments it requires.


Plan parameters with a greyed-out checkbox are required, and must be entered before the plan can be executed. 
Once all required plan parameters have been entered, and parameters pass basic syntax checks, the "Add to Queue" and "Add to Staging"
buttons will be enabled. Then you may add the plan to the queue or staging area as desired. 

Editing a Plan
~~~~~~~~~~~~~~

It is possible to edit plans already in the Queue, which is useful for making small changes to plans without having to re-add them.
The easiest way to edit a plan is to double-click on it in the Plan Queue tab, which should automatically load all of the plan
parameters into the Plan Editor tab.

.. card::

    .. image:: /_static/screenshots/plan_editor_edit.png
        :alt: Plan editor edit


From here, the plan parameters can be edited as desired. Once editing is complete, hit "Save" to update the plan in the Queue.

Plans can also be edited from the Plan Viewer tab, by clicking the "Edit" button, which will automatically shift to the Plan Editor tab.

Custom Plans
~~~~~~~~~~~~

In concert with the IPython Console tab, it is possible to add custom plans to the Plan Editor tab. This is
most useful for creating plans with no arguments that run a specific sequence of other plans. For example,

.. code:: python
    :number-lines:

    def my_custom_plan():
        yield from open_shutter()
        yield from fe_xas(dwell=1.0, eslit=0.05)
        yield from close_shutter()

Once defined in the IPython Console tab, the "Update Environment" button in the top right corner of the RUNNING PLAN box
will add the plan to the ``All Plans`` category in the Plan Editor tab.
