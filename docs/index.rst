NSLS-II Beamline GUI Framework
===============================

The NSLS-II Beamline GUI Framework (nbs-gui) provides a flexible and extensible Qt-based GUI framework for beamline control and monitoring at NSLS-II. It includes:

* Modular tab-based interface
* Real-time device monitoring
* Sample management
* Plan execution
* Mode-based device management

Getting Started
---------------

To install nbs-gui:

.. code-block:: bash

   pip install -e .

Features
--------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   mode_management
   api

Development
-----------

This project is part of the `xraygui <https://github.com/xraygui>`_ organization on GitHub.

Dependencies
------------

* Python 3.8+
* Qt (via qtpy)
* Redis
* Bluesky
* Ophyd