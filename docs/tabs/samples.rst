Samples Tab
===========

The Samples tab manages sample information, positioning, and experimental metadata. It provides tools for organizing samples and coordinating sample changes with measurement plans.

.. card::

   .. image:: /_static/screenshots/samples_overview.png
      :alt: Samples tab interface
      :align: center

Features
--------

**Sample Database**
   Store and retrieve sample information and metadata.

**Position Management**
   Record and restore sample positions.

**Experimental Tracking**
   Associate samples with measurement runs and conditions.

**Plan Integration**
   Coordinate sample changes with automated measurement sequences.

Creating Samples
-----------------

From the Samples tab
~~~~~~~~~~~~~~~~~~~~

1. Click **Add Sample** button
2. Enter sample information:
   * Name
   * Unique Identifier
   * Description (optional)
   * Position (X,Y,Z,R)
   * Proposal (optional)
3. Save to database

.. card::

   .. image:: ../_static/screenshots/add_sample_from_tab.png
      :alt: Sample creation dialog
      :align: center

.. note::

   * The Sample ID must be unique. Commonly, we use a three-digit number, where the first number indicates the side of the sampleholder
   * The position needs to be entered as a list of coordinates, e.g, ``[0, 0, 350, 45]`` for an X,Y,Z,R position.
   * Description is optional, but can be very useful, as it will be saved with each scan.

From the Beamline Status tab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Click **Add Current Position as New Sample** button
2. Enter sample information:
   * Name
   * Unique Identifier
   * Description (optional)
3. Save to database

.. card::

   .. image:: ../_static/screenshots/add_sample_from_manip.png
      :alt: Add current position as new sample dialog
      :align: center

Plan Integration
----------------

The most powerful feature of samples, is the ability to automatically move to a sample position for measurements.
This has the following benefits

* Sample metadata can be automatically saved with each scan
* Sample positions can be recorded and used repeatedly, with no risk of mistyping coordinates
* The "Multiple Samples" option in the Plan Widgets makes it easy to run identical scans on multiple samples sequentially

See :doc:`queue_control` for more information on how to use samples in measurement plans.

See Also
--------

* :doc:`../workflows` - Sample management workflows
* :doc:`../configuration` - Sample tab configuration
* :doc:`../development/plugins` - Custom sample management extensions