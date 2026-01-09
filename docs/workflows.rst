Common Workflows
================

This guide covers typical beamline operations using nbs-gui. Each workflow includes step-by-step instructions and tips for efficient operation.

Basic Motor Movement
--------------------

Moving a single motor is the most fundamental operation.

.. card::

   .. image:: _static/screenshots/motor_control_detail.png
      :alt: Detailed motor control interface
      :align: center


1. Open the **Beamline Status** tab
2. Locate the desired motor in the motor drop-down menu
3. Click in the position input field
4. Enter the target position
5. Press Enter or click the "Move" button. The setpoint should update to the entered position.
6. The status indicator should turn green during movement, and the readback should update.
7. The indicator will turn grey when the motor has stopped moving.


.. tip::

   * Many motors have limits. The GUI cannot yet display these limits, but EPICS should reject moves that are outside the limits.
   * Use relative moves for fast adjustments. The step size can be adjusted using the input between the < and > buttons.
   * An individual motor can be gracefully stopped by clicking the "Stop" button.
   * All moving motors can be stopped by clicking the "Emergency Stop" button in the header.

Simple Scan Setup
-----------------

**Creating and running a basic motor step scan**

.. card::

   .. image:: _static/screenshots/step_scan_widget.png
      :alt: Step scan widget
      :align: center

1. Open the **Queue Control** tab
2. In the Plan Editor (left panel), select **Plan Widgets** tab
3. Choose **Step Scan** from the plan type dropdown
4. Select the motor to scan from the "motor to move" dropdown
5. Enter scan parameters:

   * Start
   * End
   * Number of points
   * Exposure time per point

6. Click **Add to Queue**
7. Click **Start** in the "Queue" box in the header to execute
8. Monitor progress in the **Running Plan** box, and the Live Table tab.

There are many more options in the Step Scan widget, which are common to most plans. They are covered in greater detail in the :doc:`tabs/queue_control` guide.

.. note:: 
   All active detectors will be recorded automatically for each step of the scan.

**Console Alternative:**

Code can be run in the console tab, exactly as it would be run in a normal Bluesky terminal.

.. code-block:: python

   # Simple motor scan
   RE(scan([detector], motor_x, 0, 10, 100))

Energy Scan Experiment
----------------------

NBS-GUI has been designed for X-ray Absorption Spectroscopy beamlines, so XAS plans have a built-in widget for step scans with pre-set regions, assuming that XAS plans have been loaded into nbs-bl.

.. card::
   
   .. image:: _static/screenshots/xas_widget.png
      :alt: XAS widget
      :align: center

1. Select "XAS" from the Plan Type Selection drop-down menu
2. Select the XAS scan region from the XAS Scan drop-down. The scan steps will be displayed below. 

   * For the selected Iron L-edge scan, the scan region [690, 1, 700, 0.5, 704, ...] indicates that the energy will be scanned from 690 to 700 eV in 1 eV steps, then from 700 to 704 eV in 0.5 eV steps, etc
   * Regions can be edited or added by clicking the "Edit XAS regions" button.


Sample Management Workflow
--------------------------

Managing samples for multi-sample experiments.

1. **Define samples with known positions:**

   * Open **Samples** tab
   * Click **Add Sample**
   * Enter sample information:

     * Name and description
     * X, Y, Z, Theta positions for manipulator

2. **Record actual positions:**

   * Position sample using manipulators
   * Click "Add Current Position as New Sample" in the Beamline Status tab
   * Save position with descriptive name

3. **Go to sample:**

   * Select a sample using the drop-down menu in the Sample Selection box of the Beamline Status tab
   * Select offsets in X (inboard/outbord), Y (up/down), and Theta, compared to the saved position, and clicke "Move Sample"

4. **Use sample in a plan:**

   * Most plans have a "Sample Selection" box. Select "One Sample" or "Multiple Samples" from the drop-down menu, and then choose either one or more samples. The manipulator will be automatically positioned at the start of the scan.

Troubleshooting Common Issues
-----------------------------

Device Connection Problems
~~~~~~~~~~~~~~~~~~~~~~~~~~

Symptoms:
   Red status indicators, "Disconnected" messages

Solutions:
   1. Check EPICS server status
   2. Verify network connectivity
   3. Restart IOCs if necessary
   4. Check device configuration in devices.toml

.. note::
   
   Devices that temporarily disconnect, or are restarted, should automatically reconnect after a few minutes. If this does not happen, check the IOC, or restart the GUI.

Motor Movement Failures
~~~~~~~~~~~~~~~~~~~~~~~

Symptoms: 
   Motor doesn't move, timeout errors

Solutions:
   1. Verify position is within limits using CSS/Phoebus
   2. Check for hardware faults
   3. Ask Beamline Staff for help

Plan Execution Errors
~~~~~~~~~~~~~~~~~~~~~

Symptoms:
   Plan fails with error messages

Solutions:
   1. Check plan parameters are valid
   2. Verify all required devices are connected
   3. Review error messages in console
   4. Test simpler plans first

Advanced Scripting
------------------

For custom operations, use the **Console** tab:

.. code-block:: python

   # Custom measurement sequence
   def iron_scan_with_shutters(repeat=1, dwell=1, eslit=0.5, **kwargs):
       # Open shutters
       yield from open_shutter()

       # Perform energy scan
       yield from fe_xas(repeat=repeat, dwell=dwell, eslit=eslit, **kwargs)

       # Close shutters
       yield from close_shutter()

The defined scan can then be used in the console:

.. code-block:: python

   RE(iron_scan_with_shutters())

Or, if "update environment" is clicked in the **Running Plan** box, the plan can be added to a queue via the **Plan Editor** widget (see :doc:`tabs/queue_control`)

Halting a plan
--------------------

**Pause a plan:**

1. Click "Pause" in the "Plan Control" box in the header

   * The plan should pause at the next step.
   * The plan can then be resumed by clicking "Resume" in the "Plan Control" box in the header, or aborted by clicking "Abort" in the "Plan Control" box in the header.

2. If "Pause" does not work, try "Pause: Immediate" in the "More" dropdown menu.
3. If a plan gets truly stuck, and cannot be halted, but will not continue, "Destroy" can be used to forcefully terminate the RunEngine environment. After this, the environment will need to be re-opened. Use only as a last resort!


See Also
--------

* :doc:`getting_started` - Basic GUI introduction
* :doc:`tabs/index` - Detailed tab documentation
* :doc:`configuration` - Configuration options
* :doc:`../development/plans` - Creating custom measurement plans