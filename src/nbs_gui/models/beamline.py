"""GUI-specific beamline model with mode management."""

import time

from nbs_core.beamline import BeamlineModel as CoreBeamlineModel
from nbs_core.autoload import loadFromConfig, _find_deferred_devices
from qtpy.QtCore import Signal, QTimer

from ..load import instantiateGUIDevice
from .redis import RedisStatusProvider
from .signal_tuple import SignalTupleModel
from .base import PVModel
from ..views.signal_tuple import SignalTupleMonitor, SignalTupleControl


class GUIBeamlineModel(CoreBeamlineModel):
    """GUI-specific beamline model with mode management.

    This subclass adds mode management and device availability tracking
    to the core BeamlineModel.
    """

    # Signal emitted when mode changes

    def __init__(self, config, *args, mode_override=None, **kwargs):
        """Initialize with raw config.

        Parameters
        ----------
        config : dict
            Raw configuration dictionary from devices.toml
        """
        self.config = config
        self.mode_model = None

        default_mode = "default"
        if mode_override is not None:
            default_mode = mode_override
        print("Beamline loadFromConfig")
        # First pass: load devices available in default mode only
        print(f"Beamline config: {config}")
        base_devices, base_groups, base_roles = loadFromConfig(
            config, instantiateGUIDevice, load_pass="auto", mode=default_mode
        )


        # Determine current mode value if mode device exists
        target_mode = default_mode
        print("Beamline target_mode", target_mode)
        if "mode" in base_roles:
            mode_device = base_devices.get(base_roles["mode"])
            if mode_device is not None:
                try:
                    raw = mode_device.obj.get()
                    if hasattr(mode_device, "enum_strs") and mode_device.enum_strs:
                        if isinstance(raw, (int, float)) and 0 <= int(raw) < len(
                            mode_device.enum_strs
                        ):
                            target_mode = mode_device.enum_strs[int(raw)]
                        else:
                            target_mode = str(raw)
                    else:
                        target_mode = str(raw)
                except Exception as e:
                    print(f"Error reading initial mode from mode device: {e}")

        # Identify deferred devices from the default-mode perspective
        deferred_devices, _, deferred_config = _find_deferred_devices(
            config, mode=default_mode
        )

        # Second pass: load only deferred devices that are active in target_mode
        extra_devices = {}
        extra_groups = {}
        extra_roles = {}
        # Only perform second pass if the mode changed and there is deferred config
        if deferred_config and target_mode != default_mode:
            extra_devices, extra_groups, extra_roles = loadFromConfig(
                deferred_config,
                instantiateGUIDevice,
                load_pass="auto",
                mode=target_mode,
                filter_deferred=True,
            )

        # Merge devices, groups, and roles
        devices = dict(base_devices)
        devices.update(extra_devices)

        groups = dict(base_groups)
        for g, devs in extra_groups.items():
            if g in groups:
                groups[g].extend(devs)
            else:
                groups[g] = list(devs)

        roles = dict(base_roles)
        roles.update(extra_roles)

        super().__init__(devices, groups, roles, *args, **kwargs)
        self.update_interval_ms = 500
        self.drain_budget_ms = 20
        self._drain_cursor = 0
        self._update_timer = QTimer()
        self._update_timer.setInterval(self.update_interval_ms)
        self._update_timer.timeout.connect(self._drain_all_devices)
        self._update_timer.start()


    def loadDevices(self, devices, groups, roles):
        """Load devices and handle mode configuration."""
        super().loadDevices(devices, groups, roles)

        # Check if mode model was loaded
        if "mode" in roles:
            try:
                self.mode_model = devices[roles["mode"]]
                if self.mode_model is not None:
                    try:
                        self.mode_model.mode_changed.connect(self._on_mode_change)
                        # Apply initial mode to all devices
                        if hasattr(self.mode_model, "current_mode"):
                            self._update_device_availability(
                                self.mode_model.current_mode
                            )
                    except Exception as e:
                        print(f"Error setting up mode model: {e}")
                        self.mode_model = None
            except Exception as e:
                print(f"Error loading mode model: {e}")
                self.mode_model = None

    def _on_mode_change(self, mode, **kwargs):
        """Handle mode changes from mode model.

        Parameters
        ----------
        value : any
            New mode value (will be converted to string)
        """

        print(f"Mode changed to: {mode}")

        # Update device availability
        self._update_device_availability(mode)

    def _update_device_availability(self, mode):
        """Update availability of all devices based on mode.

        Parameters
        ----------
        mode : str
            New mode name
        """
        print(f"Updating device availability for mode: {mode}")
        for group in self.groups:
            group_dict = getattr(self, group)
            for name, device in group_dict.items():
                if hasattr(device, "set_available"):
                    try:
                        # Get mode info from config
                        device_config = self.config.get(name, {})
                        available = self._check_mode_availability(device_config, mode)
                        print(f"Device {name}: available={available}")
                        device.set_available(available)
                    except Exception as e:
                        print(f"Error updating {name} availability: {e}")

    def _check_mode_availability(self, device_config, mode):
        """Check if device is available in specified mode.

        Parameters
        ----------
        device_config : dict
            Raw device configuration
        mode : str
            Mode to check

        Returns
        -------
        bool
            Whether device is available
        """
        modes = device_config.get("_modes", [])

        if not modes:
            # No modes specified, always available
            return True
        elif mode in modes:
            # Mode explicitly allowed
            return True
        else:
            # Mode not allowed
            return False

    def reload_for_mode(self, mode):
        """
        Reload devices in place for a new mode without reinstantiating
        already-loaded devices when possible.

        Parameters
        ----------
        mode : str
            Target mode name.

        Returns
        -------
        None
        """
        existing_devices = dict(self.devices)
        existing_keys = set(existing_devices.keys())
        if self.mode_model is not None:
            try:
                self.mode_model.mode_changed.disconnect(self._on_mode_change)
            except Exception:
                pass
        self.mode_model = None

        try:
            _, filtered_config, _ = _find_deferred_devices(self.config, mode=mode)
        except Exception as exc:
            print(f"Failed to filter config for mode {mode}: {exc}")
            return None

        def instantiate_or_reuse(name, device_config, **kwargs):
            if name in existing_devices:
                return existing_devices[name]
            return instantiateGUIDevice(name, device_config, **kwargs)

        try:
            devices_new, groups_new, roles_new = loadFromConfig(
                filtered_config,
                instantiate_or_reuse,
                load_pass="auto",
                filter_deferred=False,
                mode=mode,
            )
        except Exception as exc:
            print(f"Reload failed during loadFromConfig for mode {mode}: {exc}")
            return None

        removed = existing_keys.difference(devices_new.keys())
        for name in removed:
            device = existing_devices.get(name)
            if hasattr(device, "set_available"):
                try:
                    device.set_available(False)
                except Exception as exc:
                    print(f"Failed to disable removed device {name}: {exc}")

        self.devices = {}
        self.groups = list(self.default_groups)
        for group in self.default_groups:
            setattr(self, group, {})
        self.roles = ["energy", "primary_manipulator", "default_shutter"]

        self.loadDevices(devices_new, groups_new, roles_new)
        try:
            self._update_device_availability(mode)
        except Exception as exc:
            print(f"Availability update failed for mode {mode}: {exc}")

    def _drain_all_devices(self):
        """
        Deliver pending updates from all devices within a time budget.

        Returns
        -------
        None
        """
        devices = list(self._iter_all_models())
        total = len(devices)
        if total == 0:
            return

        if self._drain_cursor >= total:
            self._drain_cursor = 0

        start = time.perf_counter()
        budget = self.drain_budget_ms / 1000.0

        processed = 0
        idx = self._drain_cursor
        while processed < total:
            device = devices[idx]
            if hasattr(device, "drain_pending") and callable(device.drain_pending):
                try:
                    device.drain_pending()
                except Exception as exc:
                    print(f"Drain failed for {getattr(device, 'name', 'unknown')}: {exc}")
            processed += 1
            idx = (idx + 1) % total
            if (time.perf_counter() - start) >= budget:
                break

        self._drain_cursor = idx

    def _iter_all_models(self):
        """
        Yield all models including nested sub-models.

        Yields
        ------
        BaseModel
            Each model to be drained.
        """
        seen = set()

        def walk(obj):
            if id(obj) in seen:
                return
            seen.add(id(obj))
            if hasattr(obj, "drain_pending") and callable(obj.drain_pending):
                yield obj
            if hasattr(obj, "iter_models") and callable(obj.iter_models):
                for sub in obj.iter_models() or ():
                    yield from walk(sub)

        for device in self.devices.values():
            yield from walk(device)
