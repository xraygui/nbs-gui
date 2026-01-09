Plan Widgets Tab
----------------

The Plan Widgets tab allows a variety of common plans to be created interactively, and added to the queue. 
For a simple example of using the widget, see :doc:`../../workflows`.

One of the most flexible plans, the Step Scan plan, is shown below. This plan widget is divided into four sections, 
which are typical of many plans. We will discuss each section in turn.

.. card::
   
   .. image:: ../../_static/screenshots/step_scan_widget.png
      :alt: Plan editor with available widgets
      :align: center


Scan Parameters
~~~~~~~~~~~~~~~

The Scan Parameters section allows the user to set parameters that are unique to the selected scan. 
These are ususally the parameters that must be set for the scan to be run. We will present the parameters
for the Step Scan plan. We endeavor to name parameters consistently so that, for example, the exposure time will always be called
"Dwell time per step".

.. card:: Parameters for Step Scan

   Motor to Move
      A drop-down menu that allows a motor selection
   Start
      A float input field that gives the starting motor position
   End
      A float input field that gives the ending motor position
   Number of points
      An integer input field that gives the number of points to scan
   Dwell time per step
      A float input field that gives the amount of time detectors will record at each point of the scan.


These parameters will usually be self-explanatory, but there is sometimes hover text to explain the parameter in more detail.

.. Note::

   You may be wondering why there are no parameters for the detectors. 
   Unlike in basic Bluesky, the detectors are selected automatically based on a list of active detectors, so there
   is no need to specify them.

Sample Selection
~~~~~~~~~~~~~~~~

The Sample Selection section allows the user to select the sample(s) to be scanned. 
If samples have been added to the :doc:`../samples` tab, they can be selected from the dropdown menu

.. card:: Sample Select Options
   
   No Sample:
      Do not move the manipulator at all.

   One Sample:
      If "One Sample" is selected, a dropdown menu of all samples will appear. The user can select the sample to be scanned. The manipulator will be moved to the selected sample before the scan is run.

   Multiple Samples:
      If "Multiple Samples" is selected, a sample select button will appear. The user can select any number of samples to be scanned. When "Add to Queue" is clicked, one individual scan will be added for each sample selected.

.. card:: Sample Offset
   
   Optionally, an offset may be added to the saved position for the selected sample. This may be useful for quickly scanning multiple spots on a sample.
   Sample offset parameters will only be displayed if one or more samples are selected.

   x offset: 
      Beam inboard/outboard adjustment
   y offset: 
      Beam up/down adjustment
   r offset: 
      Beam angle adjustment

Scan Setup
~~~~~~~~~~

Scan Setup offers generically useful options that are common to all plans. It is never required to set these parameters. 

.. card::

   Repeat:
      The number of times to repeat the scan, useful for ensuring that multiple identical scans are run on one sample.
   Group Name:
      A name for the group of scans, which will be saved in the metadata. This is useful for identifying the scans in Tiled afterwards.
   Comment:
      An arbitrary comment to be saved in the metadata, which can be used to provide additional information about the sample conditions, motivation, etc.

Beamline Setup
~~~~~~~~~~~~~~

Beamline setup allows the user to modify the beamline properties before the scan is run. Not all beamlines will have all options.

.. card::

   Exit Slit:
      The value of the exit slit opening to be set before the scan is run.
   Polarization:
      The Undulator polarization to be set before the scan is run (if applicable).
   Energy Reference:
      The reference sample to be used for the scan, if a motorized energy reference is available. The default (Auto) will attempt to select the appropriate reference sample automatically, for XAS scans.
   Energy:
      The energy to be set before the scan is run. (Useful for scans that do not otherwise set the energy)

.. attention::

   The most commonly modified parameter is the Exit Slit. It is important to note that if the Exit Slit is not set explicitly
   in the Beamline Setup, it will remain at the last set value. If the Exit Slit needs to be changed for different scans,
   it is safest to explicitly set the Exit Slit in every scan. Otherwise, the Exit Slit value may be dependent on the scan order.

Standard Plan Types
~~~~~~~~~~~~~~~~~~~

.. card::

   Step Scan:
      A basic step scan plan, which moves a single motor in a series of steps.
   XAS Scan:
      A plan for X-ray absorption spectroscopy scans, which moves the energy in a pre-set region with variable step sizes.
   Time Scan:
      A plan for measurement over a fixed time period without moving any motors.
   Variable Step Scan:
      A plan for scanning a motor with variable step sizes.
   Fly Scan:
      A plan for fly scans, which moves a motor continuously from start to stop at a given speed.
   Move Sample:
      A plan for moving a sample to a specific position (no measurement is made).
   Movement:
      A plan for moving a motor to a specific position (no measurement is made).

Subtypes
~~~~~~~~

Some plans have subtypes, which are selected from a dropdown menu. For example, the Step Scan plan has the following subtypes:

Scan:
   Absolute position scan. Motors go to the positions specified.
Relative:
   Move the motors relative to the current position.

The movement plan will have similar options.

Adding a Plan to the Queue
~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the plan has been created, it can be added to the queue by clicking the "Add to Queue" button. The button will be enabled
when all required parameters have been set. Usually, these are the parameters in **Scan Parameters**. It is never required to modify
**Scan Setup** or **Beamline Setup** in order to add a plan. If **Sample Selection** is not **No Sample**, it is required to select a sample.

.. attention::
   If you have entered all required parameters, but "Add to Queue" is still disabled, try hitting "Enter", or clicking
   out of the input field. This triggers the validation check. If "Add to Queue" is still disabled, be sure you have really
   filled all required fields, including drop-downs!

It is possible to add a plan to either the main queue, or the staging queue. The difference will be discussed below. It is possible to add a plan multiple times.
