# NSLS-II Beamline GUI Framework

A flexible and extensible Qt-based GUI framework for beamline control and monitoring at NSLS-II.

## Features

- Modular tab-based interface
- Real-time device monitoring
- Sample management system
- Plan execution interface
- Mode-based device management
- Redis-based state synchronization

## Installation

```bash
# Clone the repository
git clone https://github.com/xraygui/nbs-gui.git
cd nbs-gui

# Install in development mode
pip install -e .
```

## Dependencies

- Python 3.8+
- Qt (via qtpy)
- Redis
- Bluesky
- Ophyd

## Documentation

Documentation is available at [https://xraygui.github.io/nbs-gui](https://xraygui.github.io/nbs-gui)

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details. 