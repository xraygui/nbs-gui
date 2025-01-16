"""GUI-specific beamline model with mode management."""

from nbs_core.beamline import BeamlineModel as CoreBeamlineModel
from nbs_core.autoload import loadFromConfig
from qtpy.QtCore import Signal

from ..load import instantiateGUIDevice


class GUIBeamlineModel(CoreBeamlineModel):
    """GUI-specific beamline model with mode management.

    This subclass adds mode management and device availability tracking
    to the core BeamlineModel.
    """

    # Signal emitted when mode changes

    def __init__(self, config, *args, **kwargs):
        """Initialize with raw config.

        Parameters
        ----------
        config : dict
            Raw configuration dictionary from devices.toml
        """
        # Store raw config for mode info
        self.config = config

        # Load devices from config
        devices, groups, roles = loadFromConfig(
            config, instantiateGUIDevice, load_pass="auto"
        )

        super().__init__(devices, groups, roles, *args, **kwargs)
        self.mode_model = None

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
