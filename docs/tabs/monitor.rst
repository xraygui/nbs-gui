Monitor Tab
===========

The Monitor tab provides real-time visualization of motor positions, detector signals, and other devices.
This page varies greatly by beamline

.. card::

   .. image:: /_static/screenshots/monitor_overview.png
      :alt: Monitor tab showing device states
      :align: center

General Features
----------------

Ring Signals:
   Status signals from the ring and beamline. Usually, the ring_current should be displayed, along with the accelerator status
   and other important PVs.

Shutters:
   If the beamline has shutters or valves defined, they should be displayed in their own group, with open and close buttons.

Detectors:
   Signals from scalar detectors can be displayed in real-time. Some detectors may have gain settings.

Energy Control:
   Most beamlines should have the energy controls prominently displayed. Settings will vary by insertion device.

Motor Controls:
   All devices grouped as Motors should be available in a drop-down list, so that they can be individually displayed and moved.

Sample Selection:
   If the beamline has a manipulator with a sampleholder, there will be controls to define sample positions based on the current manipulator position.

Motors
------

**Basic Motor Operation**

.. card::

   .. image:: /_static/screenshots/motor_control_detail.png
      :alt: Detailed motor control interface
      :align: center

1. Click in the position input field
2. Enter the target position
3. Press Enter or click the "Move" button. The setpoint should update to the entered position.
4. The status indicator should turn green during movement, and the readback should update.
5. The indicator will turn grey when the motor has stopped moving.

**Pseudo Motors**

Some motors are pseudo-positioners, which translate a set of physical motors into a more useful set of "pseudo-motors".
A common example is a hexapod manipulator, which has 6 physical motors that control the position of the sampleholder, which
are translated into "virtual" X, Y, Z, Pitch, Yaw, and Roll motors. 

Another example would be a slit device, which often transforms a top slit and bottom slit into a center and width.

A third example is the energy control device, which often maps a single energy to a grating angle, pre-mirror pitch, and undulator gap, 
and maps a polarization to a set of undulator phase motors.

We can switch between the real motor an pseudo motor view by right-clicking on the motor box and selecting 
"Show Real Motors" or "Show Pseudo Motors". An example of the real and pseduo views for an energy device is shown below.
Note that the real and pseudo views may have different numbers of motors!

.. grid::

   .. grid-item-card:: Real Motors

      .. image:: /_static/screenshots/real_motor.png
         :alt: Real motor view
         :align: center

   .. grid-item-card:: Pseudo Motors

      .. image:: /_static/screenshots/pseudo_motor.png
         :alt: Pseudo motor view
         :align: center

.. attention::

   In some cases, such as for the energy device, moving an individual real axis will result in an undefined pseudo-motor position.
   For example, if the monochromator and gap are moved independently, there is no defined energy for the beamline.
   In these cases, it is best to always use the pseudo-axes. However, the real axes can be valuable for debugging purposes, especially
   in the case where a real axis is "misbehaving"

.. Note::

   It is rare that a hexapod will actually expose the real motor positions
