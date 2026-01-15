Architecture Overview
=====================

nbs-gui follows a Model-View architectural pattern for Qt applications, adapted for Ophyd and EPICS devices.
The framework separates data management (Models) from user interface (Views) to provide flexibility and maintainability.

Models
------

Our Models typically wrap Ophyd devices, which are used for hardware communication. The Qt models then provide:

* **Data Access** - Uniform interface to Ophyd devices and EPICS PVs
* **State Management** - Track device connection and operational status
* **Qt Integration** - Emit signals for UI updates
* **Error Handling** - Manage connection failures and timeouts

The Qt models are a "thin wrapper" around the Ophyd devices, providing a uniform interface for the UI, and
Qt-specific features like signals. In this sense, we may be more akin to a Model-View-ViewModel architecture, with Ophyd as the underlying 
"business logic", and our Qt models as a "ViewModel" that facilitates communication between the Model and the View. But
this sort of hair-splitting is usually not worth the effort, and we will refer to the Qt classes as "Models" for brevity.

BaseModel
~~~~~~~~~

Nearly all models inherit from the ``BaseModel`` class, which provides core functionality for all models. Let us look
at a simplified API for ``BaseModel``:

.. dropdown:: BaseModel API

   .. code-block:: python

      class BaseModel(QWidget, ModeManagedModel):
         default_controller = None
         default_monitor = PVMonitor
         connectionStatusChanged = Signal(bool)

         def __init__(self, name, obj, group, long_name, **kwargs):
            super().__init__()
            self.name = name
            self.obj = obj
            self.group = group
            self.label = long_name
            ... # Futher initialization code

         def _value_changed(self, value, **kwargs):
            raise NotImplementedError("Subclasses must implement _value_changed")

         def _stash_value(self, value, **kwargs):
            """
            Store the latest value from a subscription callback.

            Parameters
            ----------
            value : any
                  Latest value from the device.
            """
            self._latest_value = value
            self._has_update = True

         def drain_pending(self):
            """
            Emit a pending update if one exists.

            Returns
            -------
            bool
                  True if an update was emitted, otherwise False.
            """
            if not self._has_update:
                  return False
            value = self._latest_value
            self._latest_value = None
            self._has_update = False
            self._value_changed(value)
            return True

What does ``BaseModel`` provide? 

First, we see the default_controller and default_monitor attributes, which store the
View classes that will be used to control and monitor the model. Each model should know what type of View it needs, so that
interfaces can be generated automatically.

Next, we see the connectionStatusChanged signal, which is emitted to indicate that the device is connected or disconnected.
This is used to update the View's connection status indication.

We see that the initialization takes 

name:
   A name for the model, used to identify the model in the UI. Typically, the name of the Ophyd device is used.
obj:
   An Ophyd device
group:
   A list of groups the model belongs to.
long_name:
   A long name for the model, used to give the model a human-readable name in the UI.

Finally, we see three methods that are used to handle value changes from the Ophyd device.

``_value_changed(self, value, **kwargs)``:
   This method is called when the value of the model changes. It is used to update the model's internal state, and emit a properly formatted value, if appropriate.
``_stash_value(self, value, **kwargs)``:
   This method is called by the Ophyd device, and is used to quickly store the latest value from a subscription callback.
``drain_pending(self)``:
   This method is called by the View to trigger a pending update if appropriate.

This combination of methods provides a way to handle subscriptions from Ophyd quickly, and then rate-limit the updates to the UI.
Nearly all models inherit from ``BaseModel``. In order to successfully inherit from ``BaseModel``, you need three primary things:

1. Implement an ``_initialize`` method that sets up the model's connection to the Ophyd device, and subscribes to value changes.
2. Implement a ``_value_changed`` method that takes the raw model value, and emits valueChanged for the UI.
3. Implement a valueChanged signal that emits the properly formatted value for the UI.

PVModelRO
~~~~~~~~~~

``PVModelRO`` is a subclass of ``BaseModel`` that is most commonly used as base for subclassing other standard EPICS PVs,
and it implements all of these requirements. We will look in detail at how initialization works, via the ``PVModelRO`` API

.. dropdown:: PVModelRO API

   .. code-block:: python

      class PVModelRO(BaseModel):
         valueChanged = Signal(str)

         def __init__(self, name, obj, group, long_name, **kwargs):
            # print(f"[{name}.__init__] Initializing PVModelRO")
            super().__init__(name, obj, group, long_name, **kwargs)
            # print(f"[{name}.__init__] about to call _initialize")
            PVModelRO._initialize(self)

         @initialize_with_retry
         def _initialize(self):
            # print(f"[{self.name}._initialize] Initializing PVModelRO")
            if not super()._initialize():
                  self.value_type = None
                  self.units = None
                  return False

            if hasattr(self.obj, "metadata"):
                  self.units = self.obj.metadata.get("units", None)
                  # print(f"{self.name} has units {self.units}")
            else:
                  self.units = None
                  # print(f"{self.name} has no metadata")

            try:
                  _value_type = self.obj.describe().get("dtype", None)
                  if _value_type == "integer":
                     self.value_type = int
                  elif _value_type == "number":
                     self.value_type = float
                  elif _value_type == "string":
                     self.value_type = str
                  else:
                     self.value_type = None
            except Exception as e:
                  print(f"[{self.name}] Error in _initialize value_type: {e}")
                  self.value_type = None
            # print(f"[{self.name}] value_type: {self.value_type}")
            self.sub_key = self.obj.subscribe(self._stash_value, run=False)
            initial_value = self._get_value(check_connection=False)
            self._stash_value(initial_value)
            # print(f"[{self.name}] Initial value: {initial_value}")
            QTimer.singleShot(5000, self._check_value)
            # print(f"[{self.name}] PVModelRO Initialized")
            return True

         def _cleanup(self):
            self.obj.unsubscribe(self.sub_key)

         @requires_connection
         def _get_value(self):
            return self.obj.get(connection_timeout=0.2, timeout=0.2)

         def _check_value(self):
            value = self._get_value()
            self._stash_value(value)
            QTimer.singleShot(10000, self._check_value)

         def _value_changed(self, value, print_value=False, **kwargs):
            """Handle value changes, with better type handling."""
            # print(f"[{self.name}] _value_changed: {value}")
            if value is None:
                  if self._value is None:
                     return
                  else:
                     self._value = None
                     self.valueChanged.emit(self._value)
                     return

            try:
                  # Extract value from named tuple if needed
                  if hasattr(value, "_fields"):
                     if hasattr(value, "user_readback"):
                        value = value.user_readback
                     elif hasattr(value, "readback"):
                        value = value.readback
                     elif hasattr(value, "value"):
                        value = value.value

                  # Format based on type
                  if self.value_type is float:
                     formatted_value = formatFloat(value)
                  elif self.value_type is int:
                     formatted_value = formatInt(value)
                  else:
                     formatted_value = str(value)
                  if print_value:
                     print(f"[{self.name}] value changed to {formatted_value}")

                  if self._value != formatted_value:
                     self._value = formatted_value
                     self.valueChanged.emit(formatted_value)
            except Exception as e:
                  print(f"[{self.name}] Error in _value_changed for value {value}: {e}")
                  self._value = str(value)
                  self.valueChanged.emit(str(value))

         @property
         def value(self):
            return self._value

Device Initialization
~~~~~~~~~~~~~~~~~~~~~

The ``_initialize`` method sets up the subscription to the Ophyd device, using Ophyd's built in subscription mechanism.
It also checks the connection to the Ophyd device, and sets the value_type based on the Ophyd device's describe() method.
It then sets up a timer to check the value of the Ophyd device every 10 seconds, as a fallback if we miss a subscription
callback. This ensures that the UI is always up to date, and we don't have stale values for devices that change infrequently.

.. attention::
   Initialization is critically important, and has ended up being fairly complex. If you are implementing a new model,
   try to understand exactly what is going on, and why.

   .. dropdown:: Initialization Specifics

      First, look at the ``__init__`` method. It calls ``PVModelRO._initialize(self)``, which is the entry point for the initialization process.
      You may expect us to use ``self._initialize()``, and rely on MRO to call the appropriate method. However, this actually does not work
      as expected, due to the way we layer and re-try initialization. As a thought experiment, imagine the initialization process for 
      a subclass of ``PVModelRO``, called ``PVModel``. The ``PVModel`` class is going to call ``super().__init__()``, 
      which will call the ``__init__`` method of the ``PVModelRO`` class, which then calls ``BaseModel.__init__``. We need to ensure that
      ``_initialize`` is called for each layer of the inheritance chain, in the correct order. If we used ``self._initialize()`` everywhere,
      then ``BaseModel.__init__`` would call ``PVModel._initialize()``, which has overridden the base class method. Then we would need to
      have each ``_initialize`` method call ``super()._initialize()``. Then we end up with the following problems: 

      * ``PVModel._initialize()`` may depend on ``BaseModel._initialize()`` already being complete, leading to lots of required checks
      * The initialization chain will be called once per class in the inheritance chain, leading to a lot of redundant work
         - ``BaseModel.__init__`` calls ``PVModel._initialize()``, which then calls ``PVModelRO._initialize()``, which then calls ``BaseModel._initialize()``
         - ``PVModelRO.__init__`` calls ``PVModel._initialize()``, which then calls ``PVModelRO._initialize()``, which then calls ``BaseModel._initialize()``
         - ``PVModel.__init__`` calls ``PVModel._initialize()``, which then calls ``PVModelRO._initialize()``, which then calls ``BaseModel._initialize()``

      There are undoubtedly better ways to solve the problem, but the current convention is that every class only calls its own
      _initialize method, and does so explicitly.

      Especially important is the use of the ``@initialize_with_retry`` decorator on the ``_initialize`` method. This is a custom decorator that
      is used to retry the initialization of the model if it fails. On startup, it may take a few seconds to get connections to Ophyd
      devices, and we want to avoid blocking the startup process. This also provides robustness against transient connection issues,
      and IOCs that are offline during GUI startup.

      In general, try to follow this order as closely as possible:

      1. Call ``super().__init__()`` first in the ``__init__`` method of your subclass.
      2. Do all the device-independent setup you need to do in the subclass ``__init__`` method.
      3. Call ``<Class Name>._initialize()`` at the end of ``__init__``
      4. Your subclass _initialize should be decoreted with ``@initialize_with_retry``
      5. Your subclass _initialize should start with  ``super()._initialize()`` and check the return value.
      6. Do all the device-dependent setup you need to do in the subclass _initialize method, and return True if successful.

      It's complicated, but Ophyd devices were never designed to be used in this way, and it works surprisingly well.

Fortunately, most of the time you will not need to implement such a low-level model. ``PVModel``, ``EnumModel``,  and ``MotorModel`` will handle
most of the common EPICS PVs.

Compound Models
~~~~~~~~~~~~~~~

Just as Ophyd Devices are usually hierarchically composed objects that contain other, simpler Ophyd devices, we can
easily make hierarchically composed Qt models.

A simple example is ``SignalTupleModel``, which is a model that contains a tuple of other models.

.. code-block:: python

   class SignalTupleModel(BaseModel):
      """Wrapper model for a collection of signal models."""

      default_monitor = SignalTupleMonitor # set by beamline to SignalTupleMonitor
      default_controller = SignalTupleControl  # set by beamline to SignalTupleControl

      def __init__(self, name, obj, group, long_name, **kwargs):
         super().__init__(name, obj, group, long_name, **kwargs)
         names = getattr(obj, "component_names", []) or []
         self.signals = [PVModel(comp, getattr(obj, comp), group, f"{long_name}.{comp}") for comp in names]
         self.keys = list(names)

      def iter_models(self):
         """
         Yield contained signal models for traversal.

         Yields
         ------
         BaseModel
            Contained signal models.
         """
         yield from self.signals

Here, we don't need to worry about initialization, which is really handled by the PVModels we are instantiating.
The entire class is really just an easy way to iterate over ``obj.component_names`` and initialize a PVModel for each one,
and store them in a list. These sorts of models make it easy to create re-usable views for compound devices.

For example, any model that can be considered a "tuple of signals" can be made to look like a SignalTupleModel, and re-use
the views that have already been written. This is true even if the device is not a tuple, but a more complex hierarchy of devices.
We can choose to expose just the signals we want as ``self.signals``, and the views will handle the rest.

Compound models like this should provide an ``iter_models`` method that yields the contained models for traversal. 


Views
-----

Views handle user interface presentation and interaction. They:

* **Display Data** - Show model state to users
* **Handle Input** - Process user actions and commands
* **Update Automatically** - Respond to model signals

Monitors vs Controllers
~~~~~~~~~~~~~~~~~~~~~~~

We have broken our views into two Categories

.. grid:: 2

   .. grid-item-card:: Monitors

      Monitors are read-only displays of a model's value, or values. It should always be safe to display a monitor,
      and every model should have a default monitor defined.

   .. grid-item-card:: Controllers

      Controllers are any widget that allows the user to interact with the model. Not all models are controllable,
      for example, read-only PVs (like the ring current!). A controller may often include the monitor as a sub-component, along
      with one or more input fields. 

PVMonitor
~~~~~~~~~

The most basic view is ``PVMonitor``, which is a simple read-only display of the value of a PV. At its core, this
is just a ``QLabel`` that is hooked up to the model's ``valueChanged`` signal.

.. code-block:: python

   class PVMonitor(QWidget):
      """Monitor a generic PV with fixed-width styling."""

      def __init__(self, model, parent_model=None, orientation="v", **kwargs):
         """
         Initialize the monitor widget.

         Parameters
         ----------
         model : object
            The model to monitor.
         parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
         orientation : str, optional
            The orientation of the monitor ('h' or 'v').
         """
         super().__init__(**kwargs)
         print(f"Initializing PVMonitor for model: {model.label}")
         self.model = model

         if orientation == "v":
            box = QVBoxLayout()
         else:
            box = QHBoxLayout()
         box.setContentsMargins(2, 1, 2, 1)
         box.setSpacing(2)

         # Label with expanding space after it
         self.label = QLabel(model.label)
         box.addWidget(self.label)

         # Right-aligned value display with sunken frame
         self.value = QLabel("")

         if model.units is not None:
            self.units = model.units
         else:
            self.units = ""

         box.addWidget(self.value)

         if orientation == "h":
            box.setAlignment(Qt.AlignVCenter)

         self.model.valueChanged.connect(self.setText)
         print(f"[{self.model.name}] PVMonitor initial setText: {self.model.value}")
         self.setText(self.model.value)
         self.setLayout(box)

      def setText(self, val):
         """Update the displayed value.

         Parameters
         ----------
         val : str
            Formatted value to display
         """
         if val is None:
            val = "Disconnected"
         self.value.setText(f"{val} {self.units}")

Notice how the view is much more simple than the corresponding model. We have taken great pains to make the views easy to
program. There is typically no need to implement multiple models for the same device, but there are a multitude of 
possible ways to display that model, based on the circumstances. Therefore, we have tried to make it easy to create new views.

Model Controllers have so far been left out of our discussion. They are also fairly simple

.. code-block:: python

   class PVControl(QWidget):
      def __init__(self, model, parent_model=None, orientation="v", **kwargs):
         """Initialize PV control widget with type-specific validation.

         Parameters
         ----------
         model : PVModel
            Model containing the PV to control
         parent_model : object, optional
            The direct parent of the model in the widget/model hierarchy, if any. Defaults to None.
         orientation : str, optional
            Layout orientation ('v' for vertical, 'h' for horizontal)
         **kwargs : dict
            Additional arguments passed to QWidget
         """
         super().__init__(**kwargs)
         print(f"Initializing PVControl for model: {model.label}")
         self.model = model

         if orientation == "v":
            box = QVBoxLayout()
         else:
            box = QHBoxLayout()

         # Label with expanding space after it
         self.label = QLabel(model.label)
         box.addWidget(self.label)
         box.addStretch()

         # Right-aligned value display with sunken frame
         self.value = QLabel("")

         # Fixed-width input field
         self.edit = QLineEdit("")

         # Set up input validation based on value_type
         if model.value_type is float:
            self.edit.setValidator(QDoubleValidator())
         elif model.value_type is int:
            self.edit.setValidator(QIntValidator())

         if model.units is not None:
            self.units = model.units
         else:
            self.units = ""

         # Fixed-width set button
         self.setButton = QPushButton("Set")
         self.setButton.clicked.connect(self.enter_value)

         box.addWidget(self.value)
         box.addWidget(self.edit)
         box.addWidget(self.setButton)

         self.model.valueChanged.connect(self.setText)
         print(f"[{self.model.name}] PVControl initial setText: {self.model.value}")
         self.setText(self.model.value)
         self.setLayout(box)

      def enter_value(self):
         """Process and validate the entered value before setting."""
         try:
            text = self.edit.text()
            if self.model.value_type is float:
                  val = float(text)
            elif self.model.value_type is int:
                  val = int(text)
            else:
                  val = text
            self.model.set(val)
         except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e), QMessageBox.Ok)

As we can see, this is very simple, consisting of a label, an input field, and a set button. The set button calls the ``enter_value`` method,
which validates the input, and calls the model's ``set`` method. Models which are controllable need to have a ``set`` method.

SignalTuple Views
~~~~~~~~~~~~~~~~~

What about our SigalTupleModel? We have a simple group-box based view that displays a list of signals.

.. code-block:: python

   class SignalTupleBox(QWidget):
      """Group box wrapper for a collection of signal models."""

      def __init__(self, model, parent_model=None, title=None, **kwargs):
         super().__init__(**kwargs)
         self.model = model
         self.parent_model = parent_model
         box_title = title if title is not None else model.label
         self.group = QGroupBox(box_title)
         self.layout = QVBoxLayout()
         self.group.setLayout(self.layout)
         outer = QVBoxLayout()
         outer.setContentsMargins(0, 0, 0, 0)
         outer.addWidget(self.group)
         self.setLayout(outer)


   class SignalTupleMonitor(SignalTupleBox):
      def __init__(self, model, parent_model=None, title=None, **kwargs):
         super().__init__(model, parent_model=parent_model, title=title, **kwargs)
         for sig_model in model.signals:
            self.layout.addWidget(AutoMonitor(sig_model, parent_model))

   class SignalTupleControl(SignalTupleBox):
      def __init__(self, model, parent_model=None, title=None, **kwargs):
         super().__init__(model, parent_model=parent_model, title=title, **kwargs)
         for sig_model in model.signals:
            self.layout.addWidget(AutoControl(sig_model, parent_model))

Automatic Widget Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the SignalTuple views, we see the use of the ``AutoMonitor`` and ``AutoControl`` functions.
What are these, and why do we not call ``PVMonitor`` and ``PVControl`` directly?

Although our default ``SignalTupleModel`` consists of a list of ``PVModel`` objects, the ``SignalTupleMonitor`` could be
used to display any model that provides a list of signals. These signals may not be ``PVModel`` objects! They could
even be other SignalTupleModels! Therefore, we need to use a more generic way to create the views.

The ``AutoMonitor`` and ``AutoControl`` functions are used to create the views dynamically, based on the model type.
They are passed the model, and the parent model, and return a widget that is appropriate for the model. If we recall the
class signature for ``BaseModel``, we see that it has a ``default_monitor`` and ``default_controller`` attributes.

.. code-block:: python

   class BaseModel(QWidget, ModeManagedModel):
      default_controller = None
      default_monitor = PVMonitor

The AutoMonitor and AutoControl functions use these attributes to determine the appropriate view to create for each model.

.. attention::

   This does create a weird dependency hierarchy, where the models actually know about the views. Or at least, models
   know about a default view. This is not ideal, but there are really only two cases for new model/view creation.

   * Your downstream package defines a new model, and it uses the default views from nbs-gui.
   * Your downstream package defines a new model, and it uses a custom view.

   In both cases, there's really no risk of circular dependencies, because the views should not be importing the model
   classes, just using the public methods of the model that get passed to them. This forces us to keep views 
   device-agnostic.

   It just doesn't seem worth the effort to use a more complex plugin or discovery system to handle this.


NBS-GUI Architecture
---------------------

Not only are individual devices orgarized as a model-view pair, but the entire beamline is a model-view. At startup,
nbs-gui loads a model for the entire beamline, which contains

* Device models
* QueueServer communication model
* User Status model (ancillary communication with nbs-bl)
* Queue Staging model

This model is the heart of the GUI system. Every tab receives a reference to the model, and can access all of the devices,
communication models, status, etc.

Device Loading
~~~~~~~~~~~~~~

As described in the :doc:`configuration` documentation, device loading is controlled by the ``loaders`` section 
of the configuration file. Each entry in the loaders section maps an Ophyd class name to a model loader 
entry point. Each key should correspond to a class name from the _target field of a device in your devices.toml file.
Devices which do not have a corresponding loader entry will not be loaded at all in the GUI.

All loaded devices will be available in the beamline model, and can be accessed by any tab or model. Devices
are additionally organized into groups and roles, which help make the GUI creation process automatic and flexible.

For example, the Monitor tab does not reference any devices directly, because it is not specific to any one beamline, and
the device names are a-priori unknown. However, it can create a display for all *gatevalves* in the beamline, by 
using the gatevalves group in the beamline model. Likewise for motors, signals, etc.

So any device may be added or removed from the "motor control" drop-down menu by adding or removing the device from the
"motors" group in devices.toml.

Tabs
~~~~
Tabs are how we organize views into a user-friendly interface, and provide additional functionality beyond simple
model display and control. The actual tabs will be described in the :doc:`../tabs/index` documentation, but the built-in tabs
provide

* Device Monitoring and Control
* Queue Control and creation
* Console and IPython integration
* Sample management

Tabs are the easiest way to add new functionality to the GUI, and are the preferred way to add beamline-specific functionality.

Let's look briefly at the signature for a tab:

.. code-block:: python

   class MonitorTab(QWidget):
      name = "Beamline Status"
      reloadable = True

      def __init__(self, model, *args, **kwargs):
         print("Initializing Monitor Tab...")
         super().__init__(*args, **kwargs)
         self.user_status = model.user_status
         self.beamline = model.beamline
         self.model = model

As we can see, a Tab is just a QWidget subclass. It has a name, used for display in the tab bar. The top-level model
is passed to the tab at startup, and we can assign and use sub-models as needed.

In the MonitorTab, we mostly use the components of the beamline model to automatically generate a display for all of
the different devices in the beamline. Other tabs, such as the ConsoleTab, do not use devices at all, but use the
RunEngine model to connect to the IPython kernel. The sky is the limit in terms of functionality for tabs.



Plugin System
~~~~~~~~~~~~~

Tabs are loaded via Python entry points, to provide a way to add new tabs to the GUI via external packages, without
modifying the nbs-gui code.

For more details, see the source code for ``nbs_gui.mainWidget.TabViewer``, which is the class that loads and manages the tabs.

.. code-block:: python

   class TabViewer(QTabWidget):
      def __init__(self, model, *args, **kwargs):
         super().__init__(*args, **kwargs)
         self.model = model
         self._tab_order = []
         self._entry_point_map = {}

         self.setTabPosition(QTabWidget.North)
         self.setMovable(True)

         config = SETTINGS.gui_config

         tabs_to_include = config.get("gui", {}).get("tabs", {}).get("include", [])
         tabs_to_exclude = config.get("gui", {}).get("tabs", {}).get("exclude", [])

         explicit_inclusion = len(tabs_to_include) > 0
         self.tab_dict = {}
         tabs = entry_points(group="nbs_gui.tabs")

We first look in the configuration file for a list of tabs, and then we discover all of the ``nbs_gui.tabs`` entry points
and load the tabs that are listed in the configuration file.

.. attention::

   Entry points are powerful, but can be confusing. If you are going to add a new entry point, be sure you understand
   how to create an installable package, and how to register the entry point.

Plans
~~~~~

A similar system is used for plans, which are also loaded via entry points. Plans are used to create the plan widgets
that are used to create and edit plans graphically. Documentation on plans will be provided later, but plans are
loaded via the ``nbs_gui.plans`` entry point.
